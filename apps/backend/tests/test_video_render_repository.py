"""Integration tests cho `VideoRenderRepository`."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.video_render_repository import VideoRenderRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from core.enums import Industry, MediaType, VideoRenderEngine, VideoRenderStatus


@pytest.mark.asyncio
async def test_video_render_repository_crud(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    ws_repo = WorkspaceRepository(db_session)
    media_repo = MediaRepository(db_session)
    render_repo = VideoRenderRepository(db_session)

    user = await user_repo.create(
        email=f"editor_{uuid4().hex[:6]}@havi.vn",
        name="Chủ Tiệm Spa",
        password_hash="test_hash",
    )
    ws = await ws_repo.create(
        name="Havi Spa & Nails",
        industry=Industry.SPA,
        owner_user_id=user.id,
    )

    # 1. Create Job
    job = await render_repo.create(
        workspace_id=ws.id,
        title="Reels Clip Giới Thiệu Spa",
        target_aspect_ratio="9:16",
        edit_plan={"cuts": [], "captions": []},
        renderer_engine=VideoRenderEngine.FFMPEG,
    )
    assert job.id is not None
    assert job.status == VideoRenderStatus.QUEUED
    assert job.progress_percent == 0

    # 2. Set Rendering
    await render_repo.set_rendering(job_id=job.id)
    job_running = await render_repo.get(workspace_id=ws.id, job_id=job.id)
    assert job_running is not None
    assert job_running.status == VideoRenderStatus.RENDERING
    assert job_running.progress_percent >= 10

    # 3. Update Progress
    await render_repo.update_progress(job_id=job.id, progress_percent=55)
    job_updated = await render_repo.get(workspace_id=ws.id, job_id=job.id)
    assert job_updated.progress_percent == 55

    # 4. Complete Job with Output Media
    out_media = await media_repo.create(
        workspace_id=ws.id,
        object_key=f"workspaces/{ws.id}/rendered/{job.id}.mp4",
        filename="Reels.mp4",
        content_type="video/mp4",
        type=MediaType.VIDEO,
    )
    await render_repo.complete(
        job_id=job.id,
        output_media_id=out_media.id,
        output_url="https://storage.havi.vn/rendered.mp4",
    )

    job_completed = await render_repo.get(workspace_id=ws.id, job_id=job.id)
    assert job_completed.status == VideoRenderStatus.COMPLETED
    assert job_completed.progress_percent == 100
    assert job_completed.output_media_id == out_media.id
    assert job_completed.output_url == "https://storage.havi.vn/rendered.mp4"

    # 5. List for workspace
    items, total = await render_repo.list_for_workspace(
        workspace_id=ws.id, status=VideoRenderStatus.COMPLETED
    )
    assert total >= 1
    assert any(item.id == job.id for item in items)
