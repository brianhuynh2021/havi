"""Job định kỳ do Celery Beat kích hoạt (xem scheduler/beat.py)."""

import asyncio
import logging

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
