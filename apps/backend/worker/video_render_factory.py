"""Factory dựng VideoRender dependencies trong worker."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from adapters.persistence.db import session_scope
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.video_render_repository import VideoRenderRepository
from adapters.storage.object_storage import ObjectStorage
from adapters.video_renderers.ffmpeg_renderer import FFmpegVideoRenderer
from core.config import get_settings


@dataclass
class VideoRenderWorkerContext:
    render_repo: VideoRenderRepository
    media_repo: MediaRepository
    event_repo: EventLogRepository
    storage: ObjectStorage
    renderer: FFmpegVideoRenderer


@asynccontextmanager
async def video_render_scope() -> AsyncGenerator[VideoRenderWorkerContext]:
    settings = get_settings()
    storage = ObjectStorage(settings)
    renderer = FFmpegVideoRenderer()

    async with session_scope() as session:
        render_repo = VideoRenderRepository(session)
        media_repo = MediaRepository(session)
        event_repo = EventLogRepository(session)

        yield VideoRenderWorkerContext(
            render_repo=render_repo,
            media_repo=media_repo,
            event_repo=event_repo,
            storage=storage,
            renderer=renderer,
        )
