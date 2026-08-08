"""Dựng PublishService trong worker/scheduler.

Cùng lý do và cùng khuôn với `content_engine_factory`: worker không có FastAPI
dependency injection nên phải tự lắp, nhưng dùng đúng repository/adapter mà API
dùng để không nhân đôi business rule (SYSTEM_ARCHITECTURE.md §0).
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.db import session_scope
from adapters.persistence.publish_repository import PublishRepository
from adapters.publishers.facebook import FacebookPublisher
from adapters.publishers.fake import FakePublisher
from application.services.publish_service import PublishService
from core.config import get_settings
from core.enums import Channel
from domain.ports.publisher import PublisherPort

logger = logging.getLogger(__name__)


def build_publishers() -> dict[Channel, PublisherPort]:
    """Map kênh → adapter.

    Chỉ Facebook có mặt. Zalo/Google vắng ở đây là cố ý: `PublishService.run_job`
    gặp kênh không có adapter sẽ `mark_failed` với `VALIDATION_PERMANENT` và
    không retry — tốt hơn nhiều so với một adapter rỗng báo thành công giả.
    """
    settings = get_settings()
    if settings.use_fake_publisher:
        # Chỉ tới được đây khi HAVI_ENV=local — Settings ném lỗi lúc khởi động
        # nếu bật fake ở staging/production.
        logger.warning(
            "Publish đang chạy FAKE (HAVI_USE_FAKE_PUBLISHER=true) — không có bài "
            "nào lên Facebook thật. Đặt false để đăng thật."
        )
        return {Channel.FACEBOOK_PAGE: FakePublisher()}
    return {Channel.FACEBOOK_PAGE: FacebookPublisher(settings)}


@asynccontextmanager
async def publish_service_scope() -> AsyncGenerator[PublishService]:
    """Một session cho cả lượt chạy: commit khi xong, rollback nếu ném lỗi."""
    async with session_scope() as session:
        yield PublishService(
            content=ContentRepository(session),
            connections=ConnectionRepository(session),
            publishes=PublishRepository(session),
            publishers=build_publishers(),
        )
