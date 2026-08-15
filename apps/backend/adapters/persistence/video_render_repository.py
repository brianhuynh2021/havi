"""Repository cho VideoRenderJob (Phase 3 Video Pipeline)."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import VideoRenderEngine, VideoRenderStatus
from domain.models.video_render import VideoRenderJob


class VideoRenderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workspace_id: UUID,
        title: str = "Video ngắn tự động",
        target_aspect_ratio: str = "9:16",
        edit_plan: dict[str, Any] | None = None,
        renderer_engine: VideoRenderEngine = VideoRenderEngine.FFMPEG,
        source_media_id: UUID | None = None,
    ) -> VideoRenderJob:
        job = VideoRenderJob(
            workspace_id=workspace_id,
            title=title,
            target_aspect_ratio=target_aspect_ratio,
            edit_plan=edit_plan or {},
            renderer_engine=renderer_engine,
            source_media_id=source_media_id,
            status=VideoRenderStatus.QUEUED,
            progress_percent=0,
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, *, workspace_id: UUID, job_id: UUID) -> VideoRenderJob | None:
        result = await self._session.execute(
            select(VideoRenderJob).where(
                VideoRenderJob.id == job_id,
                VideoRenderJob.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, job_id: UUID) -> VideoRenderJob | None:
        """Dùng cho background worker khi đã có job_id."""
        result = await self._session.execute(
            select(VideoRenderJob).where(VideoRenderJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_for_workspace(
        self,
        *,
        workspace_id: UUID,
        status: VideoRenderStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[VideoRenderJob], int]:
        filters = [VideoRenderJob.workspace_id == workspace_id]
        if status is not None:
            filters.append(VideoRenderJob.status == status)

        count_query = select(func.count(VideoRenderJob.id)).where(*filters)
        total = (await self._session.execute(count_query)).scalar_one()

        items_query = (
            select(VideoRenderJob)
            .where(*filters)
            .order_by(VideoRenderJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self._session.execute(items_query)).scalars().all())
        return items, total

    async def set_rendering(
        self, *, job_id: UUID, started_at: datetime | None = None
    ) -> VideoRenderJob | None:
        job = await self.get_by_id(job_id)
        if job:
            job.status = VideoRenderStatus.RENDERING
            job.started_at = started_at or datetime.now(UTC)
            job.progress_percent = max(10, job.progress_percent)
            await self._session.flush()
        return job

    async def update_progress(self, *, job_id: UUID, progress_percent: int) -> None:
        job = await self.get_by_id(job_id)
        if job and job.status == VideoRenderStatus.RENDERING:
            job.progress_percent = min(99, max(0, progress_percent))
            await self._session.flush()

    async def complete(
        self,
        *,
        job_id: UUID,
        output_media_id: UUID,
        output_url: str | None = None,
        completed_at: datetime | None = None,
    ) -> VideoRenderJob | None:
        job = await self.get_by_id(job_id)
        if job:
            job.status = VideoRenderStatus.COMPLETED
            job.progress_percent = 100
            job.output_media_id = output_media_id
            job.output_url = output_url
            job.completed_at = completed_at or datetime.now(UTC)
            job.error_message = None
            await self._session.flush()
        return job

    async def fail(self, *, job_id: UUID, error_message: str) -> VideoRenderJob | None:
        job = await self.get_by_id(job_id)
        if job:
            job.status = VideoRenderStatus.FAILED
            job.error_message = error_message[:1000]
            job.completed_at = datetime.now(UTC)
            await self._session.flush()
        return job

    async def cancel(self, *, workspace_id: UUID, job_id: UUID) -> bool:
        job = await self.get(workspace_id=workspace_id, job_id=job_id)
        if not job:
            return False
        if job.status in (VideoRenderStatus.COMPLETED, VideoRenderStatus.FAILED):
            return False
        job.status = VideoRenderStatus.CANCELLED
        job.completed_at = datetime.now(UTC)
        await self._session.flush()
        return True
