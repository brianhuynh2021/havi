"""Lịch chạy định kỳ.

Chạy scheduler:
    uv run --extra queue celery -A scheduler.beat:celery_app beat -l info
"""

from celery.schedules import crontab

from worker.celery_app import celery_app

celery_app.conf.beat_schedule = {
    # Quét content_item ở trạng thái scheduled tới giờ đăng
    "dispatch-due-posts": {
        "task": "havi.scheduler.dispatch_due_posts",
        "schedule": crontab(minute="*/5"),
    },
    # Refresh access token nền tảng trước khi hết hạn
    "refresh-platform-tokens": {
        "task": "havi.scheduler.refresh_platform_tokens",
        "schedule": crontab(hour="*/6", minute=0),
    },
    # CRM vòng đời khách: nhắc 14 / 30 ngày — soạn draft, chờ chủ duyệt
    "crm-lifecycle-nudges": {
        "task": "havi.scheduler.crm_lifecycle_nudges",
        "schedule": crontab(hour=8, minute=0),
    },
    # Chụp engagement snapshot cho tab Báo cáo (không cần real-time)
    "poll-engagement": {
        "task": "havi.scheduler.poll_engagement",
        "schedule": crontab(hour="*/3", minute=15),
    },
}
