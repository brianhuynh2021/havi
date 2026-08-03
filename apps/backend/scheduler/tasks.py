"""Job định kỳ do Celery Beat kích hoạt (xem scheduler/beat.py)."""

from worker.celery_app import celery_app


@celery_app.task(name="havi.scheduler.dispatch_due_posts")
def dispatch_due_posts() -> None:
    """Tìm content_item `scheduled` tới giờ → enqueue `havi.publish.content_item`.

    Lấy row bằng lock + idempotency key để một bài chỉ vào hàng đợi đúng một lần.
    """
    raise NotImplementedError


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
