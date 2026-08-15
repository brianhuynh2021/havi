"""Job định kỳ do Celery Beat kích hoạt (xem scheduler/beat.py)."""

import asyncio
import logging

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="havi.scheduler.dispatch_due_posts")
def dispatch_due_posts() -> None:
    """Tìm content_item `scheduled` tới giờ → tạo publish job → gọi worker chạy.

    Chỉ *tạo* job ở đây, việc gọi Graph API để `havi.publish.run_due` làm. Beat
    phải quay lại đúng nhịp: một Page chậm hay rate-limit có thể giữ một lượt
    đăng hàng chục giây, và nếu beat đứng chờ thì mọi workspace khác trễ theo.

    `enqueue` idempotent theo `(content_item_id, channel, scheduled_at)` nên beat
    chạy mỗi 5 phút, hai beat chạy chồng khi deploy, hay task bị giao lại đều
    không sinh bài trùng. Gửi `run_due` kể cả khi lượt này không tạo job mới:
    job đang chờ backoff từ lượt trước cũng cần được chạy.
    """
    from worker.publish_service_factory import publish_service_scope
    from worker.tasks import publish_run_due

    async def _run() -> tuple[int, int]:
        async with publish_service_scope() as service:
            result = await service.dispatch_due()
            return result.enqueued, result.skipped

    enqueued, skipped = asyncio.run(_run())
    logger.info("dispatch_due_posts: %d new jobs, %d skipped (existing jobs)", enqueued, skipped)
    publish_run_due.delay()


@celery_app.task(name="havi.scheduler.refresh_platform_tokens")
def refresh_platform_tokens() -> None:
    """Refresh token sắp hết hạn; hỏng thì đặt connection về `expired` để UI báo nối lại."""
    raise NotImplementedError


@celery_app.task(name="havi.scheduler.crm_lifecycle_nudges")
def crm_lifecycle_nudges() -> None:
    """Soạn tin nhắc 14 / 30 ngày. Luôn tạo `crm_message` ở `pending_approval`."""
    raise NotImplementedError


@celery_app.task(name="havi.scheduler.poll_engagement")
def poll_engagement() -> None:
    """Chụp engagement snapshot của bài đã đăng để dựng số cho tab Báo cáo."""
    raise NotImplementedError
