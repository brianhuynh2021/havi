"""Dựng InboxService trong worker.

Cùng khuôn với `publish_service_factory`: worker không có FastAPI
dependency injection nên tự lắp từ các repository/adapter.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.db import session_scope
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.inbox_repository import InboxRepository
from adapters.publishers.facebook_reply import FacebookReplyAdapter
from adapters.publishers.fake_reply import FakeReplyPublisher
from application.services.inbox_service import InboxService
from core.config import get_settings
from core.enums import Platform
from domain.ports.reply_publisher import ReplyPublisherPort


def build_reply_publishers(session) -> dict[Platform, ReplyPublisherPort]:
    settings = get_settings()
    if settings.is_local:
        return {
            Platform.FACEBOOK: FakeReplyPublisher(Platform.FACEBOOK),
            Platform.ZALO_OA: FakeReplyPublisher(Platform.ZALO_OA),
        }
    return {
        Platform.FACEBOOK: FacebookReplyAdapter(ConnectionRepository(session)),
    }


@asynccontextmanager
async def inbox_service_scope() -> AsyncGenerator[tuple[InboxService, ConnectionRepository, EventLogRepository]]:
    async with session_scope() as session:
        connections = ConnectionRepository(session)
        events = EventLogRepository(session)
        service = InboxService(
            inbox=InboxRepository(session),
            profiles=BrandProfileRepository(session),
            events=events,
            reply_publishers=build_reply_publishers(session),
        )
        yield service, connections, events
