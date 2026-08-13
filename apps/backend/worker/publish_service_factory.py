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
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.publish_repository import PublishRepository
from adapters.publishers.facebook import FacebookPublisher
from adapters.publishers.fake import FakePublisher
from adapters.publishers.google_business import GoogleBusinessPublisher
from adapters.publishers.zalo import ZaloPublisher
from application.services.publish_service import PublishService
from core.alerts import LoggingAlertSink
from core.config import get_settings
from core.enums import Channel
from domain.ports.publisher import PublisherPort

logger = logging.getLogger(__name__)


def build_publishers() -> dict[Channel, PublisherPort]:
    """Map kênh → adapter."""
    settings = get_settings()
    if settings.use_fake_publisher:
        logger.warning(
            "Publish đang chạy FAKE (HAVI_USE_FAKE_PUBLISHER=true) — không có bài "
            "nào lên mạng thật. Đặt false để đăng thật."
        )
        return {
            Channel.FACEBOOK_PAGE: FakePublisher(channel=Channel.FACEBOOK_PAGE),
            Channel.ZALO_OA: FakePublisher(channel=Channel.ZALO_OA),
            Channel.GOOGLE_BUSINESS: FakePublisher(channel=Channel.GOOGLE_BUSINESS),
        }
    return {
        Channel.FACEBOOK_PAGE: FacebookPublisher(settings),
        Channel.ZALO_OA: ZaloPublisher(),
        Channel.GOOGLE_BUSINESS: GoogleBusinessPublisher(),
    }


@asynccontextmanager
async def publish_service_scope() -> AsyncGenerator[PublishService]:
    """Một session cho cả lượt chạy: commit khi xong, rollback nếu ném lỗi."""
    async with session_scope() as session:
        yield PublishService(
            content=ContentRepository(session),
            connections=ConnectionRepository(session),
            publishes=PublishRepository(session),
            events=EventLogRepository(session),
            media=MediaRepository(session),
            alerts=LoggingAlertSink(),
            publishers=build_publishers(),
        )
