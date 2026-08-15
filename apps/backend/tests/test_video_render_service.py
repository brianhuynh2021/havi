"""Unit & integration tests cho `VideoRenderService`."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.video_render_repository import VideoRenderRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.video_render_service import VideoRenderJobNotFound, VideoRenderService
from core.enums import Industry, VideoRenderStatus


@pytest.mark.asyncio
async def test_video_render_service_lifecycle(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    ws_repo = WorkspaceRepository(db_session)
    media_repo = MediaRepository(db_session)
    event_repo = EventLogRepository(db_session)
    render_repo = VideoRenderRepository(db_session)

    user = await user_repo.create(
        email=f"service_test_{uuid4().hex[:6]}@havi.vn",
        name="Tiệm Nail Q1",
        password_hash="test_hash",
    )
    ws = await ws_repo.create(
        name="Tiệm Nail Q1",
        industry=Industry.SPA,
        owner_user_id=user.id,
    )

    service = VideoRenderService(
        render_repo=render_repo,
        media_repo=media_repo,
        event_repo=event_repo,
    )

    # 1. Create Render Job
    job = await service.create_job(
        workspace_id=ws.id,
        title="Mẫu Nail Mùa Hè 2026",
        target_aspect_ratio="9:16",
    )
    assert job.id is not None
    assert job.status == VideoRenderStatus.QUEUED
    assert job.title == "Mẫu Nail Mùa Hè 2026"

    # 2. Get Job
    fetched = await service.get_job(workspace_id=ws.id, job_id=job.id)
    assert fetched.id == job.id

    # 3. List Jobs
    items, total = await service.list_jobs(workspace_id=ws.id)
    assert total >= 1
    assert any(i.id == job.id for i in items)

    # 4. Cancel Job
    cancelled = await service.cancel_job(workspace_id=ws.id, job_id=job.id)
    assert cancelled is True
    job_cancelled = await service.get_job(workspace_id=ws.id, job_id=job.id)
    assert job_cancelled.status == VideoRenderStatus.CANCELLED

    # 5. Retry Job
    job_retried = await service.retry_job(workspace_id=ws.id, job_id=job.id)
    assert job_retried.status == VideoRenderStatus.QUEUED
    assert job_retried.progress_percent == 0


@pytest.mark.asyncio
async def test_video_render_service_nonexistent_job(db_session: AsyncSession):
    render_repo = VideoRenderRepository(db_session)
    media_repo = MediaRepository(db_session)
    event_repo = EventLogRepository(db_session)

    service = VideoRenderService(
        render_repo=render_repo,
        media_repo=media_repo,
        event_repo=event_repo,
    )

    with pytest.raises(VideoRenderJobNotFound):
        await service.get_job(workspace_id=uuid4(), job_id=uuid4())
