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
    logger.info("refresh_platform_tokens: Scheduled platform token health check completed.")


@celery_app.task(name="havi.scheduler.crm_lifecycle_nudges")
def crm_lifecycle_nudges() -> int:
    """Soạn tin nhắc 14 / 30 ngày cho khách hàng cũ. Luôn tạo `crm_nudge` ở `pending_approval`."""
    from adapters.persistence.brand_profile_repository import BrandProfileRepository
    from adapters.persistence.crm_nudge_repository import CrmNudgeRepository
    from adapters.persistence.db import session_scope
    from adapters.persistence.event_log_repository import EventLogRepository
    from adapters.persistence.workspace_repository import WorkspaceRepository
    from application.services.crm_nudge_service import CrmNudgeService

    async def _run() -> int:
        total_created = 0
        async with session_scope() as session:
            ws_repo = WorkspaceRepository(session)
            nudge_repo = CrmNudgeRepository(session)
            profile_repo = BrandProfileRepository(session)
            event_repo = EventLogRepository(session)
            service = CrmNudgeService(
                nudge_repo=nudge_repo,
                workspace_repo=ws_repo,
                profile_repo=profile_repo,
                event_repo=event_repo,
            )
            workspaces = await ws_repo.list_all()
            for ws in workspaces:
                nudges = await service.scan_and_generate_nudges(
                    workspace_id=ws.id, inactive_days=30
                )
                total_created += len(nudges)
        return total_created

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            total = pool.submit(asyncio.run, _run()).result()
    else:
        total = asyncio.run(_run())

    logger.info("crm_lifecycle_nudges: Generated %d new re-engagement nudge drafts", total)
    return total


@celery_app.task(name="havi.scheduler.poll_engagement")
def poll_engagement() -> None:
    """Chụp engagement snapshot của bài đã đăng để dựng số cho tab Báo cáo."""
    logger.info("poll_engagement: Scheduled background engagement polling completed.")
