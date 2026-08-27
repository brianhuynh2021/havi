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
from datetime import UTC, datetime
from uuid import UUID

from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.content_prompt import (
    PILOT_CHANNELS,
    build_system_prompt,
    build_user_prompt,
)
from application.services.content_service import ContentJobNotFound, WorkspaceNotFound
from core.content_state import initial_status
from core.enums import Channel, MediaStatus
from core.events import EventLogEntry
from domain.models.content import ContentItem, ContentJob
from domain.policies.content_output import output_json_schema, parse_and_validate
from domain.policies.provider_router import AllProvidersFailed, ProviderRouter
from domain.ports.llm import LLMRequest

logger = logging.getLogger("havi.content_engine")


class GenerationFailed(Exception):
    """Mọi provider đều thất bại — job chuyển sang `failed` với reason rõ."""


@dataclass
class GenerationResult:
    job: ContentJob
    items: list[ContentItem]


def _job_elapsed_ms(job: ContentJob) -> int:
    """Latency người dùng chờ: từ lúc API tạo job, gồm cả thời gian trong queue."""
    created_at = job.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return max(0, round((datetime.now(UTC) - created_at).total_seconds() * 1000))


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
        connections: ConnectionRepository | None = None,
    ) -> None:
        self._content = content
        self._workspaces = workspaces
        self._profiles = profiles
        self._media = media
        self._events = events
        self._router = router
        self._connections = connections

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

        # Chủ tiệm chọn rõ "Bài viết" hoặc "Video ngắn" trước khi tạo. Router
        # lưu lựa chọn cùng raw_inputs để worker nền nhận được mà không cần thêm
        # cột DB chỉ dành cho metadata của một job.
        creative_inputs = [
            raw
            for raw in job.raw_inputs
            if not (isinstance(raw, dict) and raw.get("meta") == "channels_filter")
        ]
        requested_channel_values = next(
            (
                raw.get("target_channels")
                for raw in job.raw_inputs
                if isinstance(raw, dict) and raw.get("meta") == "channels_filter"
            ),
            None,
        )
        has_explicit_channel_filter = requested_channel_values is not None
        target_channels: list[Channel] = []
        for value in requested_channel_values or []:
            try:
                channel = Channel(value)
            except ValueError:
                continue
            if channel in PILOT_CHANNELS and channel not in target_channels:
                target_channels.append(channel)
        if not target_channels:
            target_channels = list(PILOT_CHANNELS)

        media_descriptions = await self._describe_media(
            workspace_id=workspace_id, raw_inputs=creative_inputs
        )
        few_shot_examples: list[str] = []
        try:
            from core.enums import ContentStatus

            recent_items, _ = await self._content.list_items(
                workspace_id=workspace_id,
                status=ContentStatus.PUBLISHED,
                limit=2,
            )
            if not recent_items:
                recent_items, _ = await self._content.list_items(
                    workspace_id=workspace_id,
                    status=ContentStatus.APPROVED,
                    limit=2,
                )
            few_shot_examples = [item.text for item in recent_items if item.text]
        except Exception as exc:
            logger.debug("Failed to query few-shot memory: %s", exc)

        request = LLMRequest(
            system_prompt=build_system_prompt(workspace, profile, target_channels=target_channels),
            user_prompt=build_user_prompt(
                workspace=workspace,
                raw_inputs=creative_inputs,
                media_descriptions=media_descriptions,
                target_channels=target_channels,
                few_shot_examples=few_shot_examples,
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
                    input_summary=f"{len(creative_inputs)} raw input",
                    duration_ms=_job_elapsed_ms(job),
                    error=reason,
                )
            )
            await self._content.mark_job_failed(job, reason=reason)
            raise GenerationFailed(reason) from exc

        # Trích xuất URL ảnh nếu người dùng có nạp ảnh vào đầu vào
        uploaded_media_url = None
        for raw in job.raw_inputs or []:
            if isinstance(raw, dict):
                if raw.get("preview_url"):
                    uploaded_media_url = raw.get("preview_url")
                    break
                elif raw.get("media_asset_id"):
                    try:
                        asset_id = UUID(str(raw["media_asset_id"]))
                        asset = await self._media.get(workspace_id=workspace_id, asset_id=asset_id)
                        if asset:
                            from adapters.storage.object_storage import ObjectStorage
                            from core.config import get_settings

                            storage = ObjectStorage(get_settings())
                            uploaded_media_url = storage.public_url(asset.object_key)
                    except Exception as err:
                        logger.warning("Failed to resolve media asset url: %s", err)
                    if uploaded_media_url:
                        break
            elif hasattr(raw, "preview_url") and raw.preview_url:
                uploaded_media_url = raw.preview_url
                break
            elif hasattr(raw, "media_asset_id") and raw.media_asset_id:
                try:
                    asset = await self._media.get(
                        workspace_id=workspace_id, asset_id=raw.media_asset_id
                    )
                    if asset:
                        from adapters.storage.object_storage import ObjectStorage
                        from core.config import get_settings

                        storage = ObjectStorage(get_settings())
                        uploaded_media_url = storage.public_url(asset.object_key)
                except Exception as err:
                    logger.warning("Failed to resolve media asset url: %s", err)
                if uploaded_media_url:
                    break

        status = initial_status(workspace.publish_mode)
        items = []
        for draft in result.value.drafts:
            # Prompt đã yêu cầu đúng tập kênh, nhưng vẫn lọc ở boundary để một
            # output LLM thừa kênh không làm user nhận cả bài viết lẫn video.
            if has_explicit_channel_filter and draft.channel not in target_channels:
                continue
            item_media_url = uploaded_media_url
            item = await self._content.create_item(
                workspace_id=workspace_id,
                job_id=job_id,
                channel=draft.channel,
                kind=draft.kind,
                text=draft.text,
                media_note=draft.media_note,
                media_url=item_media_url,
                status=status,
            )
            items.append(item)
        await self._content.mark_job_drafts_ready(job)

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_id=job_id,
                job_kind="content.generate_drafts",
                input_summary=f"{len(creative_inputs)} raw input",
                output_summary=(
                    f"{len(items)} draft, provider={result.served_by}, "
                    f"attempts={len(result.attempts)}, "
                    f"provider_latency_ms={result.response.latency_ms}"
                ),
                # Cộng cả lần thử thất bại — provider trả output lỗi vẫn tốn token.
                tokens_in=result.total_tokens_in,
                tokens_out=result.total_tokens_out,
                # SLA P1 tính thời gian người dùng thật sự chờ, không chỉ thời
                # gian HTTP của provider: queue nghẽn 30 giây + model 2 giây vẫn
                # là một job 32 giây đối với người dùng.
                duration_ms=_job_elapsed_ms(job),
                provider=result.served_by.value,
                model=result.response.model,
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
                logger.warning("Job using uncompleted media asset %s", asset.id)
                continue
            descriptions.append(f"{asset.type.value}: {asset.filename}")
        return descriptions
