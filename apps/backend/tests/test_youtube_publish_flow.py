"""Integration tests for YouTube Shorts publishing, video constraints, and quota flow."""

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.publish_repository import PublishRepository
from adapters.publishers.youtube import YouTubePublisher
from application.services.publish_service import PublishService
from core.enums import Channel, ConnectionStatus, ContentStatus, Industry, Platform, PublishStatus
from core.token_crypto import encrypt_token
from domain.models.connection import PlatformConnection
from domain.models.content import ContentItem
from domain.models.publish import PublishJob
from domain.models.user import User
from domain.models.workspace import Workspace
from domain.policies.youtube_quota import record_quota_consumption
from tests.test_youtube_quota import MockRedis


@pytest.mark.asyncio
async def test_youtube_shorts_publish_success_increments_quota(
    db_session: AsyncSession, monkeypatch
):
    """Publish YouTube Shorts thành công ghi nhận 1600 units quota và cập nhật trạng thái."""
    user = User(name="YT Owner", email=f"yt_pub_{uuid4()}@havi.vn", password_hash="hash")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="YT Pub WS", industry=Industry.SPA, owner_user_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    conn = PlatformConnection(
        workspace_id=ws.id,
        platform=Platform.YOUTUBE,
        external_account_id="UC_yt_123",
        account_name="My Shorts Channel",
        access_token_encrypted=encrypt_token("valid_yt_tok"),
        status=ConnectionStatus.CONNECTED,
    )
    db_session.add(conn)
    await db_session.flush()

    item = ContentItem(
        workspace_id=ws.id,
        channel=Channel.YOUTUBE,
        kind="video",
        text="Video Havi Spa #Shorts",
        media_url="https://havi.vn/clip.mp4",
        status=ContentStatus.APPROVED,
    )
    db_session.add(item)
    await db_session.flush()

    job = PublishJob(
        workspace_id=ws.id,
        content_item_id=item.id,
        channel=Channel.YOUTUBE,
        idempotency_key=f"idem_yt_{uuid4()}",
        status=PublishStatus.PENDING,
        scheduled_at=datetime.now(UTC),
    )
    db_session.add(job)
    await db_session.commit()

    # Mock YouTube HTTP endpoints
    def _yt_handler(req: httpx.Request) -> httpx.Response:
        if "uploadType=resumable" in str(req.url):
            return httpx.Response(200, headers={"Location": "https://upload.youtube.com/session_123"}, request=req)
        if "upload.youtube.com" in str(req.url):
            return httpx.Response(200, json={"id": "yt_video_new_id_999"}, request=req)
        return httpx.Response(200, content=b"fake_mp4_bytes", request=req)

    transport = httpx.MockTransport(_yt_handler)
    yt_client = httpx.AsyncClient(transport=transport)
    publisher = YouTubePublisher(client=yt_client)

    redis = MockRedis()

    service = PublishService(
        content=ContentRepository(db_session),
        connections=ConnectionRepository(db_session),
        publishes=PublishRepository(db_session),
        events=EventLogRepository(db_session),
        publishers={Channel.YOUTUBE: publisher},
        redis_client=redis,
    )

    result_job = await service.run_job(job)
    assert result_job.status == PublishStatus.SUCCEEDED
    assert result_job.external_post_id == "yt_video_new_id_999"

    # Quota đã tiêu thụ 1600 units
    used_val = await redis.get(f"youtube_quota:{datetime.now(UTC).date().isoformat()}")
    assert used_val is not None
    assert int(used_val) >= 1600


@pytest.mark.asyncio
async def test_youtube_shorts_quota_exhausted_defers_job(
    db_session: AsyncSession
):
    """Khi daily quota đã hết (<1600 units), job được reschedule sang 00:00 giờ Pacific hôm sau."""
    user = User(name="YT Owner", email=f"yt_quota_{uuid4()}@havi.vn", password_hash="hash")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="YT Quota WS", industry=Industry.SPA, owner_user_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    conn = PlatformConnection(
        workspace_id=ws.id,
        platform=Platform.YOUTUBE,
        external_account_id="UC_yt_quota",
        account_name="My Shorts Channel",
        access_token_encrypted=encrypt_token("valid_yt_tok"),
        status=ConnectionStatus.CONNECTED,
    )
    db_session.add(conn)
    await db_session.flush()

    item = ContentItem(
        workspace_id=ws.id,
        channel=Channel.YOUTUBE,
        kind="video",
        text="Video Havi Spa #Shorts",
        media_url="https://havi.vn/clip.mp4",
        status=ContentStatus.APPROVED,
    )
    db_session.add(item)
    await db_session.flush()

    job = PublishJob(
        workspace_id=ws.id,
        content_item_id=item.id,
        channel=Channel.YOUTUBE,
        idempotency_key=f"idem_yt_{uuid4()}",
        status=PublishStatus.PENDING,
        scheduled_at=datetime.now(UTC),
    )
    db_session.add(job)
    await db_session.commit()

    redis = MockRedis()
    now_utc = datetime.now(UTC)
    # Ghi nhận quota đã dùng 8800 units (còn 1200 units, < 1600 units cần thiết)
    await record_quota_consumption(redis, units=8800, now_utc=now_utc)

    service = PublishService(
        content=ContentRepository(db_session),
        connections=ConnectionRepository(db_session),
        publishes=PublishRepository(db_session),
        events=EventLogRepository(db_session),
        publishers={Channel.YOUTUBE: YouTubePublisher()},
        redis_client=redis,
    )

    result_job = await service.run_job(job)
    # Job không bị fail, mà được giữ ở PENDING với next_attempt_at và failure_detail rõ ràng
    assert result_job.status == PublishStatus.PENDING
    assert result_job.next_attempt_at is not None
    assert result_job.next_attempt_at > now_utc
    assert "Hết hạn mức YouTube hôm nay" in (result_job.failure_detail or "")
