"""Factory dựng dependency của luồng đăng video trong worker.

Tách khỏi `api/deps.py` vì worker không có request scope: nó tự mở session, tự
đóng, và phải làm được điều đó ngoài vòng đời của FastAPI.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from adapters.persistence.db import session_scope
from adapters.persistence.video_post_repository import VideoPostRepository
from adapters.persistence.video_publish_repository import VideoPublishRepository
from adapters.publishers.facebook import FacebookPublisher
from adapters.storage.object_storage import ObjectStorage
from application.services.video_publish_service import VideoPublishService
from core.config import get_settings


@asynccontextmanager
async def video_publish_scope() -> AsyncGenerator[VideoPublishService]:
    settings = get_settings()
    storage = ObjectStorage(settings)

    def signed_url_for(post) -> str:  # noqa: ANN001 — VideoPost
        """Ký lại mỗi lần: URL ký có hạn, và hạn đó có thể đã qua từ lúc duyệt."""
        return storage.public_url(post.source_object_key)

    async with session_scope() as session:
        from api.deps import get_connection_service  # noqa: PLC0415 — tránh vòng import

        yield VideoPublishService(
            posts=VideoPostRepository(session),
            attempts=VideoPublishRepository(session),
            connections=get_connection_service(session, settings),
            publisher=FacebookPublisher(settings),
            signed_url_for=signed_url_for,
        )
