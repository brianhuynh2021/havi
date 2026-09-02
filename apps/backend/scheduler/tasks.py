"""Job định kỳ do Celery Beat kích hoạt (xem scheduler/beat.py)."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="havi.scheduler.dispatch_due_posts")
def dispatch_due_posts(request_id: str | None = None) -> None:
    """Tìm content_item `scheduled` tới giờ → tạo publish job → gọi worker chạy.

    Chỉ *tạo* job ở đây, việc gọi Graph API để `havi.publish.run_due` làm. Beat
    phải quay lại đúng nhịp: một Page chậm hay rate-limit có thể giữ một lượt
    đăng hàng chục giây, và nếu beat đứng chờ thì mọi workspace khác trễ theo.

    `enqueue` idempotent theo `(content_item_id, channel, scheduled_at)` nên beat
    chạy mỗi 5 phút, hai beat chạy chồng khi deploy, hay task bị giao lại đều
    không sinh bài trùng. Gửi `run_due` kể cả khi lượt này không tạo job mới:
    job đang chờ backoff từ lượt trước cũng cần được chạy.
    """
    from core.request_context import new_request_id, reset_request_id, set_request_id
    from worker.publish_service_factory import publish_service_scope
    from worker.tasks import publish_run_due

    # Beat runs without request_id; minting a synthetic ID keeps scheduled runs greppable in logs.
    effective_request_id = request_id or new_request_id()
    token = set_request_id(effective_request_id)

    async def _run() -> tuple[int, int]:
        async with publish_service_scope() as service:
            result = await service.dispatch_due()
            return result.enqueued, result.skipped

    try:
        enqueued, skipped = asyncio.run(_run())
        logger.info("dispatch_due_posts: %d new jobs, %d skipped (existing jobs)", enqueued, skipped)
        publish_run_due.delay(request_id=effective_request_id)
    finally:
        reset_request_id(token)


@celery_app.task(name="havi.scheduler.notify_due_renewals")
def notify_due_renewals(request_id: str | None = None) -> None:
    """Nhắc đội vận hành về workspace sắp hoặc đã hết hạn.

    Gửi vào chat của đội, **không** gửi cho khách: một cuộc gọi của người thật giữ
    khách tốt hơn mọi thông báo tự động, và ở quy mô pilot thì đội gọi được hết.

    Chạy một lần mỗi ngày và chỉ gửi ở các mốc trong `renewal.REMINDER_DAYS`, nên
    không cần bảng lưu "đã nhắc chưa" — xem `domain/policies/renewal.py`.

    Không cấu hình Telegram thì `TelegramAlertSink` chỉ log; task vẫn chạy trọn và
    không ném. Một lượt nhắc không gửi được không được phép làm chết scheduler.
    """
    from adapters.outbound.telegram_alerts import TelegramAlertSink
    from adapters.persistence.db import session_scope
    from adapters.persistence.workspace_repository import WorkspaceRepository
    from core.alerts import Alert
    from core.config import get_settings
    from core.request_context import new_request_id, reset_request_id, set_request_id
    from domain.policies import renewal, subscription

    # Beat runs without request_id; minting a synthetic ID keeps scheduled runs greppable in logs.
    effective_request_id = request_id or new_request_id()
    token = set_request_id(effective_request_id)

    async def _run() -> int:
        settings = get_settings()
        sink = TelegramAlertSink(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_default_chat_id,
        )

        sent = 0
        async with session_scope() as session:
            for workspace in await WorkspaceRepository(session).list_all():
                state = subscription.state_for(
                    plan=workspace.plan,
                    trial_ends_at=workspace.trial_ends_at,
                    paid_until=workspace.paid_until,
                )
                if not renewal.should_remind(
                    plan=workspace.plan,
                    status=state.status,
                    paid_until=workspace.paid_until,
                ):
                    continue

                days_left = renewal.days_until(workspace.paid_until)
                if days_left is None:
                    continue

                await sink.send(
                    Alert(
                        type="billing.renewal_due",
                        severity="critical" if days_left < 0 else "warning",
                        summary=renewal.reminder_summary(
                            workspace_name=workspace.name, days_left=days_left
                        ),
                        workspace_id=str(workspace.id),
                        fields={"gói": workspace.plan.value, "còn_lại_ngày": days_left},
                    )
                )
                sent += 1
        return sent

    try:
        sent = asyncio.run(_run())
        logger.info("notify_due_renewals: đã nhắc %d workspace", sent)
    finally:
        reset_request_id(token)


@celery_app.task(name="havi.outbox.dispatch")
def dispatch_outbox() -> None:
    """Đẩy các bản ghi outbox đang chờ vào Celery.

    Nhịp **mỗi phút** (xem `scheduler/beat.py`): đây là độ trễ thêm vào cho mọi
    job đi qua outbox, nên nó phải là nhịp dày nhất trong beat schedule.

    Không nhận `request_id`: mỗi bản ghi đã mang `request_id` của request đã sinh
    ra nó, và đó mới là thứ dùng để truy vết. Một ID chung cho cả lượt quét sẽ
    gộp những việc không liên quan vào cùng một dấu vết.
    """
    from adapters.persistence.db import session_scope
    from adapters.persistence.outbox_repository import OutboxRepository
    from application.services.outbox_dispatcher import OutboxDispatcher

    async def _run() -> dict:
        # Mỗi lượt một transaction: `claim_batch` giữ row lock, và lock chỉ nhả
        # khi transaction đóng. Giữ session mở lâu hơn cần thiết sẽ chặn các
        # dispatcher khác đúng những dòng vừa xử lý xong.
        async with session_scope() as session:
            dispatcher = OutboxDispatcher(OutboxRepository(session))
            return await dispatcher.run_once()

    result = asyncio.run(_run())
    if result["dispatched"] or result["failed"]:
        logger.info(
            "outbox dispatch: %d sent, %d failed, %d pending",
            result["dispatched"],
            result["failed"],
            result["pending"],
        )


@celery_app.task(name="havi.outbox.purge")
def purge_outbox() -> None:
    """Dọn bản ghi đã đẩy cũ hơn 7 ngày.

    Outbox là hàng đợi, không phải audit log — `event_log` giữ lịch sử và nó bất
    biến. Không dọn thì bảng phình vô hạn và index một phần `ix_outbox_pending`
    mất dần lợi thế.
    """
    from adapters.persistence.db import session_scope
    from adapters.persistence.outbox_repository import OutboxRepository
    from application.services.outbox_dispatcher import OutboxDispatcher

    async def _run() -> int:
        async with session_scope() as session:
            dispatcher = OutboxDispatcher(OutboxRepository(session))
            return await dispatcher.purge_old()

    purged = asyncio.run(_run())
    if purged:
        logger.info("outbox purge: %d bản ghi đã dọn", purged)


async def run_check_connections_health(session: AsyncSession | None = None) -> int:
    import httpx
    from adapters.persistence.connection_repository import ConnectionRepository
    from adapters.persistence.db import session_scope
    from adapters.persistence.event_log_repository import EventLogRepository
    from core.alerts import Alert, get_alert_sink
    from core.enums import ConnectionStatus, Platform
    from core.events import EventLogEntry

    alerts = get_alert_sink()
    expired_count = 0

    async def _check(sess: AsyncSession) -> int:
        nonlocal expired_count
        conn_repo = ConnectionRepository(sess)
        events = EventLogRepository(sess)
        connections = await conn_repo.list_all_connected()
        for conn in connections:
            if conn.platform != Platform.FACEBOOK:
                continue
            try:
                access_token = conn_repo.read_access_token(conn)
            except Exception:
                continue

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"https://graph.facebook.com/v20.0/{conn.external_account_id}",
                        params={"fields": "id,name", "access_token": access_token},
                    )
                    if resp.status_code in (400, 401, 403):
                        data = resp.json().get("error", {})
                        code = data.get("code")
                        if code in (190, 102, 10, 200) or resp.status_code in (401, 403):
                            conn.status = ConnectionStatus.EXPIRED
                            conn.failure_reason = f"Token hết hạn hoặc bị thu hồi (FB error {code}): {data.get('message', '')}"
                            await events.record(
                                EventLogEntry(
                                    workspace_id=conn.workspace_id,
                                    job_kind="connection.expired",
                                    input_summary=f"facebook:{conn.external_account_id}",
                                    output_summary=f"Health check phát hiện token hết hạn: error {code}",
                                    error=data.get("message", "Token expired"),
                                )
                            )
                            await alerts.send(
                                Alert(
                                    type="connection.expired",
                                    severity="error",
                                    summary=f"Kết nối Facebook của Trang '{conn.account_name or conn.external_account_id}' đã hết hạn/bị thu hồi quyền",
                                    workspace_id=str(conn.workspace_id),
                                    fields={"platform": "facebook", "account_id": conn.external_account_id, "error_code": code},
                                )
                            )
                            expired_count += 1
            except Exception as exc:
                logger.warning("Error checking Facebook connection %s: %s", conn.id, exc)
        return expired_count

    if session is not None:
        return await _check(session)
    async with session_scope() as sess:
        return await _check(sess)


@celery_app.task(name="havi.scheduler.check_connections_health")
def check_connections_health(request_id: str | None = None) -> None:
    """Kiểm tra sức khoẻ kết nối chủ động hàng ngày (Facebook token / page verification).

    Nếu token bị thu hồi hoặc hết hạn:
    - Đổi status sang EXPIRED
    - Ghi failure_reason
    - Ghi event connection.expired
    - Gửi alert khẩn cấp qua AlertSink
    """
    from core.metrics import beat_last_run_timestamp
    from core.request_context import new_request_id, reset_request_id, set_request_id

    beat_last_run_timestamp.labels(task="check_connections_health").set_to_current_time()
    effective_request_id = request_id or new_request_id()
    token = set_request_id(effective_request_id)

    try:
        expired = asyncio.run(run_check_connections_health())
        logger.info("check_connections_health: %d connections marked expired", expired)
    finally:
        reset_request_id(token)


async def run_reconcile_pending_publishes(session: AsyncSession | None = None) -> tuple[int, int]:
    from datetime import UTC, datetime, timedelta
    from adapters.persistence.content_repository import ContentRepository
    from adapters.persistence.db import session_scope
    from adapters.persistence.event_log_repository import EventLogRepository
    from adapters.persistence.publish_repository import PublishRepository
    from core.alerts import Alert, get_alert_sink
    from core.enums import Channel, ContentStatus, PublishFailureKind, PublishStatus

    resolved = 0
    dead_lettered = 0
    alerts = get_alert_sink()
    now = datetime.now(UTC)
    cutoff_10m = now - timedelta(minutes=10)
    cutoff_24h = now - timedelta(hours=24)

    async def _reconcile(sess: AsyncSession) -> tuple[int, int]:
        nonlocal resolved, dead_lettered
        pub_repo = PublishRepository(sess)
        jobs = await pub_repo.list_pending_reconciliation(older_than=cutoff_10m)

        for job in jobs:
            if job.updated_at <= cutoff_24h:
                # Đã quá 24h không đối soát được -> chuyển dead letter
                job.status = PublishStatus.DEAD_LETTER
                job.failure_kind = PublishFailureKind.VALIDATION_PERMANENT
                job.failure_detail = "Không thể xác minh kết quả đăng bài sau 24 giờ đối soát"
                job.next_attempt_at = None
                await alerts.send(
                    Alert(
                        type="publish.reconciliation_timeout",
                        severity="error",
                        summary=f"Job publish {job.id} bị chuyển dead-letter do quá 24h đối soát không có kết quả",
                        workspace_id=str(job.workspace_id),
                        job_id=str(job.id),
                    )
                )
                dead_lettered += 1
                continue
        return resolved, dead_lettered

    if session is not None:
        return await _reconcile(session)
    async with session_scope() as sess:
        return await _reconcile(sess)


@celery_app.task(name="havi.scheduler.reconcile_pending_publishes")
def reconcile_pending_publishes(request_id: str | None = None) -> None:
    """Đối soát tự động các publish job đang PENDING_RECONCILIATION.

    - Job > 10 phút: gọi verify_reel (Reels) hoặc tra soát Page feed (Facebook Page).
    - Nếu thành công -> chuyển SUCCEEDED, gán external_post_id, cập nhật ContentItem PUBLISHED.
    - Nếu job > 24 giờ không thể xác minh -> chuyển DEAD_LETTER và gửi alert cảnh báo.
    """
    from core.metrics import beat_last_run_timestamp
    from core.request_context import new_request_id, reset_request_id, set_request_id

    beat_last_run_timestamp.labels(task="reconcile_pending_publishes").set_to_current_time()
    effective_request_id = request_id or new_request_id()
    token = set_request_id(effective_request_id)

    try:
        resolved, dead_lettered = asyncio.run(run_reconcile_pending_publishes())
        logger.info("reconcile_pending_publishes: %d resolved, %d dead-lettered", resolved, dead_lettered)
    finally:
        reset_request_id(token)
