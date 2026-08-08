"""Content Engine — trái tim của Havi.

Một content job = **một** lần gọi LLM sinh nhiều bản theo kênh (ROADMAP.md §1
nguyên tắc #5). Draft dừng ở `pending_approval` khi workspace ở `review_first`
(mặc định) — không bài nào lên mạng khi chủ chưa duyệt.

Luồng: đọc brand profile → dựng prompt → ProviderRouter (Gemini ưu tiên, fallback
Anthropic/OpenAI) → validate schema + banned claims → tạo content_items → ghi
event_log kèm token/latency/provider.
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.content_prompt import build_system_prompt, build_user_prompt
from core.content_state import initial_status
from core.enums import MediaStatus
from core.events import EventLogEntry
from domain.models.content import ContentItem, ContentJob
from domain.policies.content_output import output_json_schema, parse_and_validate
from domain.policies.provider_router import AllProvidersFailed, ProviderRouter
from domain.ports.llm import LLMRequest

logger = logging.getLogger("havi.content_engine")


class WorkspaceNotFound(Exception):
    pass


class ContentJobNotFound(Exception):
    pass


class GenerationFailed(Exception):
    """Mọi provider đều thất bại — job chuyển sang `failed` với reason rõ."""


@dataclass
class GenerationResult:
    job: ContentJob
    items: list[ContentItem]


class ContentEngine:
    def __init__(
        self,
        *,
        content: ContentRepository,
        workspaces: WorkspaceRepository,
        profiles: BrandProfileRepository,
        media: MediaRepository,
        events: EventLogRepository,
        router: ProviderRouter,
    ) -> None:
        self._content = content
        self._workspaces = workspaces
        self._profiles = profiles
        self._media = media
        self._events = events
        self._router = router

    async def generate_drafts(self, *, workspace_id: UUID, job_id: UUID) -> GenerationResult:
        job = await self._content.get_job(workspace_id=workspace_id, job_id=job_id)
        if job is None:
            raise ContentJobNotFound()

        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFound()
        # Brand profile là input bắt buộc của prompt — tạo lazy nếu chưa có để
        # job không chết chỉ vì chủ tiệm chưa vào Cài đặt.
        profile = await self._profiles.get(workspace_id)
        if profile is None:
            profile = await self._profiles.create(
                workspace_id=workspace_id, industry=workspace.industry
            )

        await self._content.mark_job_processing(job)

        media_descriptions = await self._describe_media(
            workspace_id=workspace_id, raw_inputs=job.raw_inputs
        )
        request = LLMRequest(
            system_prompt=build_system_prompt(workspace, profile),
            user_prompt=build_user_prompt(
                workspace=workspace,
                raw_inputs=job.raw_inputs,
                media_descriptions=media_descriptions,
            ),
            output_schema=output_json_schema(),
        )

        banned_claims = list(profile.banned_claims or [])
        try:
            result = await self._router.generate(
                request,
                validate=lambda text: parse_and_validate(text, banned_claims=banned_claims),
            )
        except AllProvidersFailed as exc:
            reason = str(exc)
            # Ghi event TRƯỚC khi `mark_job_failed` commit: cả hai cùng nằm
            # trong một transaction nên cùng sống sót. Đảo thứ tự thì event rơi
            # vào transaction mới và bị rollback cuốn đi khi `GenerationFailed`
            # ném ra.
            await self._events.record(
                EventLogEntry(
                    workspace_id=workspace_id,
                    job_id=job_id,
                    job_kind="content.generate_drafts",
                    input_summary=f"{len(job.raw_inputs)} raw input",
                    error=reason,
                )
            )
            await self._content.mark_job_failed(job, reason=reason)
            raise GenerationFailed(reason) from exc

        status = initial_status(workspace.publish_mode)
        items = [
            await self._content.create_item(
                workspace_id=workspace_id,
                job_id=job_id,
                channel=draft.channel,
                kind=draft.kind,
                text=draft.text,
                media_note=draft.media_note,
                status=status,
            )
            for draft in result.value.drafts
        ]
        await self._content.mark_job_drafts_ready(job)

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_id=job_id,
                job_kind="content.generate_drafts",
                input_summary=f"{len(job.raw_inputs)} raw input",
                output_summary=(
                    f"{len(items)} draft, provider={result.served_by}, "
                    f"attempts={len(result.attempts)}"
                ),
                # Cộng cả lần thử thất bại — provider trả output lỗi vẫn tốn token.
                tokens_in=result.total_tokens_in,
                tokens_out=result.total_tokens_out,
                duration_ms=result.response.latency_ms,
            )
        )
        return GenerationResult(job=job, items=items)

    async def _describe_media(self, *, workspace_id: UUID, raw_inputs: list[dict]) -> list[str]:
        """Mô tả file đã nạp cho prompt.

        Chưa gửi bytes ảnh cho model — vision/transcription là P1/P2
        (SYSTEM_ARCHITECTURE.md §5.3). Hiện chỉ đưa tên file + loại để model biết
        có ảnh gì, chưa "hiểu" nội dung ảnh.
        """
        descriptions: list[str] = []
        for item in raw_inputs:
            asset_id = item.get("media_asset_id")
            if not asset_id:
                continue
            asset = await self._media.get(workspace_id=workspace_id, asset_id=UUID(str(asset_id)))
            if asset is None:
                continue
            if asset.status == MediaStatus.PENDING:
                logger.warning("job dùng asset %s chưa upload xong", asset.id)
                continue
            descriptions.append(f"{asset.type.value}: {asset.filename}")
        return descriptions
