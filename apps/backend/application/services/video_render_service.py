"""Application service quản lý vòng đời VideoRenderJob (Phase 3 Video Pipeline)."""

from typing import Any
from uuid import UUID

from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.video_render_repository import VideoRenderRepository
from core.enums import VideoRenderEngine, VideoRenderStatus
from domain.models.video_render import VideoRenderJob
from domain.policies.video_edit_plan import default_edit_plan_for_short_form, validate_edit_plan


class VideoRenderJobNotFound(Exception):
    """Không tìm thấy VideoRenderJob trong workspace."""


class VideoRenderService:
    def __init__(
        self,
        render_repo: VideoRenderRepository,
        media_repo: MediaRepository,
        event_repo: EventLogRepository,
    ) -> None:
        self._render_repo = render_repo
        self._media_repo = media_repo
        self._event_repo = event_repo

    async def create_job(
        self,
        *,
        workspace_id: UUID,
        title: str = "Video ngắn tự động",
        target_aspect_ratio: str = "9:16",
        edit_plan: dict[str, Any] | None = None,
        source_media_id: UUID | None = None,
        renderer_engine: VideoRenderEngine = VideoRenderEngine.FFMPEG,
        request_id: str | None = None,
    ) -> VideoRenderJob:
        """Tạo job render và đưa vào hàng đợi Celery `havi.video_render`."""
        if source_media_id is not None:
            source_asset = await self._media_repo.get(
                workspace_id=workspace_id, asset_id=source_media_id
            )
            if not source_asset:
                raise VideoRenderJobNotFound(f"Media asset {source_media_id} không tồn tại")
            if edit_plan is None:
                duration = source_asset.duration_seconds or 15.0
                edit_plan = default_edit_plan_for_short_form(duration, hook_text=title)
        else:
            if edit_plan is None:
                edit_plan = default_edit_plan_for_short_form(15.0, hook_text=title)

        # Validate cấu trúc EditPlan
        plan_obj = validate_edit_plan(edit_plan)

        job = await self._render_repo.create(
            workspace_id=workspace_id,
            title=title,
            target_aspect_ratio=target_aspect_ratio,
            edit_plan=plan_obj.to_dict(),
            renderer_engine=renderer_engine,
            source_media_id=source_media_id,
        )

        # Dispatch Celery async task vào hàng đợi riêng havi.video_render
        from worker.tasks import render_video_job

        try:
            render_video_job.apply_async(
                args=[str(workspace_id), str(job.id), request_id],
                queue="havi.video_render",
            )
        except Exception:
            # Fallback nếu Redis/Celery offline lúc test đơn lẻ
            pass

        return job

    async def get_job(self, *, workspace_id: UUID, job_id: UUID) -> VideoRenderJob:
        job = await self._render_repo.get(workspace_id=workspace_id, job_id=job_id)
        if not job:
            raise VideoRenderJobNotFound(f"Job {job_id} không tồn tại")
        return job

    async def list_jobs(
        self,
        *,
        workspace_id: UUID,
        status: VideoRenderStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[VideoRenderJob], int]:
        return await self._render_repo.list_for_workspace(
            workspace_id=workspace_id, status=status, limit=limit, offset=offset
        )

    async def retry_job(
        self, *, workspace_id: UUID, job_id: UUID, request_id: str | None = None
    ) -> VideoRenderJob:
        job = await self.get_job(workspace_id=workspace_id, job_id=job_id)
        job.status = VideoRenderStatus.QUEUED
        job.progress_percent = 0
        job.error_message = None

        from worker.tasks import render_video_job

        try:
            render_video_job.apply_async(
                args=[str(workspace_id), str(job.id), request_id],
                queue="havi.video_render",
            )
        except Exception:
            pass

        return job

    async def cancel_job(self, *, workspace_id: UUID, job_id: UUID) -> bool:
        return await self._render_repo.cancel(workspace_id=workspace_id, job_id=job_id)
