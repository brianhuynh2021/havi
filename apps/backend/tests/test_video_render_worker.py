"""Integration tests cho Celery Video Render Worker Task."""

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.video_render_repository import VideoRenderRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from adapters.video_renderers.ffmpeg_renderer import FFmpegVideoRenderer
from core.enums import Industry, VideoRenderStatus
from worker.celery_app import celery_app
from worker.tasks import render_video_job
from worker.video_render_factory import VideoRenderWorkerContext


class MockStorage:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    async def read_object(self, key: str) -> bytes:
        return self.files.get(key, b"MOCK_STORAGE_BYTES")

    async def put_object(
        self, object_key: str, data: bytes, content_type: str = "video/mp4"
    ) -> None:
        self.files[object_key] = data

    def get_public_url(self, object_key: str) -> str:
        return f"https://storage.havi.vn/{object_key}"

    def public_url(self, object_key: str) -> str:
        return f"https://storage.havi.vn/{object_key}"


def test_video_render_task_is_registered_in_celery():
    """Xác nhận task `havi.video.render` được đăng ký và map vào hàng đợi `havi.video_render`."""
    assert "havi.video.render" in celery_app.tasks
    route = celery_app.conf.task_routes.get("havi.video.render")
    assert route == {"queue": "havi.video_render"}


@pytest.mark.asyncio
async def test_celery_render_video_job_execution(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    user_repo = UserRepository(db_session)
    ws_repo = WorkspaceRepository(db_session)
    render_repo = VideoRenderRepository(db_session)
    media_repo = MediaRepository(db_session)
    event_repo = EventLogRepository(db_session)

    user = await user_repo.create(
        email=f"worker_test_{uuid4().hex[:6]}@havi.vn",
        name="Chủ Tiệm Trà Sữa",
        password_hash="test_hash",
    )
    ws = await ws_repo.create(
        name="Trà Sữa Havi",
        industry=Industry.FOOD_BEVERAGE,
        owner_user_id=user.id,
    )

    job = await render_repo.create(
        workspace_id=ws.id,
        title="TikTok Video Review Trà Đào",
        target_aspect_ratio="9:16",
        edit_plan={
            "target_aspect_ratio": "9:16",
            "target_duration_seconds": 5.0,
            "cuts": [{"start_ms": 0, "end_ms": 5000}],
            "captions": [{"text": "TRÀ ĐÀO SIÊU NGON", "start_ms": 0, "end_ms": 3000}],
        },
    )

    mock_storage = MockStorage()
    mock_renderer = FFmpegVideoRenderer(ffmpeg_path="")  # Mock fallback

    @asynccontextmanager
    async def mock_scope():
        yield VideoRenderWorkerContext(
            render_repo=render_repo,
            media_repo=media_repo,
            event_repo=event_repo,
            storage=mock_storage,
            renderer=mock_renderer,
        )

    monkeypatch.setattr("worker.video_render_factory.video_render_scope", mock_scope)

    # Chạy worker task
    render_video_job(workspace_id=str(ws.id), job_id=str(job.id))

    # Kiểm tra trạng thái sau khi worker chạy xong
    updated_job = await render_repo.get(workspace_id=ws.id, job_id=job.id)
    assert updated_job is not None
    assert updated_job.status == VideoRenderStatus.COMPLETED
    assert updated_job.progress_percent == 100
    assert updated_job.output_media_id is not None
    assert updated_job.output_url is not None

    # Kiểm tra MediaAsset được tạo ra
    media_asset = await media_repo.get(workspace_id=ws.id, asset_id=updated_job.output_media_id)
    assert media_asset is not None
    assert media_asset.aspect_ratio == "9:16"
    assert media_asset.duration_seconds == 5.0
