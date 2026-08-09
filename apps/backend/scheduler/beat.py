"""Lịch chạy định kỳ.

Chạy scheduler:
    uv run --extra queue celery -A scheduler.beat:celery_app beat -l info
"""

from celery.schedules import crontab

from worker.celery_app import celery_app

celery_app.conf.beat_schedule = {
    # Quét content_item ở trạng thái scheduled tới giờ đăng → tạo publish job
    "dispatch-due-posts": {
        "task": "havi.scheduler.dispatch_due_posts",
        "schedule": crontab(minute="*/5"),
    },
    # Chạy publish job đến hạn. `dispatch_due_posts` đã gọi task này sau mỗi lượt
    # quét; lịch riêng ở đây là lưới an toàn cho job đang chờ backoff — backoff
    # 60s không nên phải đợi tới lượt quét 5 phút kế tiếp. `claim_due` khoá row
    # nên hai nguồn cùng gọi không đăng trùng.
    "publish-due-jobs": {
        "task": "havi.publish.run_due",
        "schedule": crontab(minute="*"),
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
