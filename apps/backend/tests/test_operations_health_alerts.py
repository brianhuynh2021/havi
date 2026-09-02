"""Unit & integration tests for operational health checks, alerts, and reconciliation."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.outbox_repository import OutboxRepository
from adapters.persistence.publish_repository import PublishRepository
from core.alerts import Alert, LoggingAlertSink, TelegramAlertSink
from core.enums import Channel, ConnectionStatus, ContentStatus, Industry, OutboxStatus, Platform, PublishFailureKind, PublishStatus
from core.events import EventLogEntry
from core.token_crypto import encrypt_token
from domain.models.connection import PlatformConnection
from domain.models.outbox import OutboxEntry
from domain.models.publish import PublishJob
from domain.models.user import User
from domain.models.workspace import Workspace
from scheduler.tasks import run_check_connections_health, run_reconcile_pending_publishes


@pytest.mark.asyncio
async def test_telegram_alert_sink_sends_post(monkeypatch):
    """TelegramAlertSink gửi POST tới Telegram bot API đúng định dạng."""
    recorded_requests = []

    def _handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(_handler)
    _orig_client = httpx.AsyncClient
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda *args, **kwargs: _orig_client(transport=transport),
    )

    sink = TelegramAlertSink(bot_token="test_token", chat_id="123456")
    alert = Alert(
        type="test.alert",
        severity="error",
        summary="Thử nghiệm cảnh báo",
        workspace_id="ws_1",
        job_id="job_1",
    )
    await sink.send(alert)

    assert len(recorded_requests) == 1
    req = recorded_requests[0]
    assert "api.telegram.org/bottest_token/sendMessage" in str(req.url)


@pytest.mark.asyncio
async def test_check_connections_health_detects_expired_token(
    db_session: AsyncSession, monkeypatch
):
    """Health check phát hiện token Facebook hết hạn (code 190) -> chuyển EXPIRED và ghi event."""
    user = User(name="Test User", email=f"health_{uuid4()}@havi.vn", password_hash="hash")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="Test Health WS", industry=Industry.SPA, owner_user_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    conn = PlatformConnection(
        workspace_id=ws.id,
        platform=Platform.FACEBOOK,
        external_account_id="page_999",
        account_name="Trang Test",
        access_token_encrypted=encrypt_token("invalid_token"),
        status=ConnectionStatus.CONNECTED,
    )
    db_session.add(conn)
    await db_session.commit()

    # Mock Facebook Graph API error response
    def _graph_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": "Error validating access token: Session has expired", "code": 190}},
            request=request,
        )

    transport = httpx.MockTransport(_graph_handler)
    _orig_client = httpx.AsyncClient
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda *args, **kwargs: _orig_client(transport=transport),
    )

    # Run health check
    await run_check_connections_health(db_session)

    # Verify connection status is now EXPIRED
    conn_repo = ConnectionRepository(db_session)
    updated_conn = await conn_repo.get(workspace_id=ws.id, platform=Platform.FACEBOOK)
    assert updated_conn is not None
    assert updated_conn.status == ConnectionStatus.EXPIRED
    assert "Token hết hạn" in (updated_conn.failure_reason or "")


@pytest.mark.asyncio
async def test_reconcile_pending_publishes_dead_letters_after_24h(
    db_session: AsyncSession
):
    """Job PENDING_RECONCILIATION quá 24h được chuyển sang DEAD_LETTER."""
    user = User(name="Test User", email=f"reconcile_{uuid4()}@havi.vn", password_hash="hash")
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="Test Reconcile WS", industry=Industry.SPA, owner_user_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    from domain.models.content import ContentItem
    item = ContentItem(
        workspace_id=ws.id,
        channel=Channel.FACEBOOK_PAGE,
        kind="post",
        text="Test content",
        status=ContentStatus.APPROVED,
    )
    db_session.add(item)
    await db_session.flush()

    old_job = PublishJob(
        workspace_id=ws.id,
        content_item_id=item.id,
        channel=Channel.FACEBOOK_PAGE,
        idempotency_key=f"idem_{uuid4()}",
        status=PublishStatus.PENDING_RECONCILIATION,
        scheduled_at=datetime.now(UTC) - timedelta(days=2),
    )
    db_session.add(old_job)
    await db_session.commit()

    # Force updated_at back 25 hours
    old_job.updated_at = datetime.now(UTC) - timedelta(hours=25)
    await db_session.commit()

    await run_reconcile_pending_publishes(db_session)

    pub_repo = PublishRepository(db_session)
    jobs = await pub_repo.list_for_workspace(workspace_id=ws.id)
    assert len(jobs) == 1
    assert jobs[0].status == PublishStatus.DEAD_LETTER
    assert "24 giờ" in (jobs[0].failure_detail or "")
