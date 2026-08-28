"""Celery app dùng chung cho worker và scheduler.

Chạy worker:
    uv run --extra queue celery -A worker.celery_app:celery_app worker -l info

Nguyên tắc: mọi việc là một job có id, đi qua hàng đợi, có retry và ghi `event_log`.
LLM chỉ chạy khi có job rõ ràng — không loop nền.
"""

from celery import Celery
from kombu import Queue

from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "havi",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["worker.tasks", "scheduler.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=360,
    task_default_queue="havi.default",
    task_queues=(
        Queue("havi.default"),
        Queue("havi.content"),
        Queue("havi.publish"),
        Queue("havi.video_publish"),
        Queue("havi.inbox"),
    ),
    task_routes={
        # Video tách khỏi bài viết: đăng video là tải hàng chục MB lên Facebook
        # rồi chờ nền tảng xử lý, có thể mất hàng phút. Chung hàng đợi với bài
        # viết thì một clip nặng giữ chân mọi bài text đang chờ.
        "havi.video.publish": {"queue": "havi.video_publish"},
        "havi.video.reconcile": {"queue": "havi.video_publish"},
        "havi.video.publish_due": {"queue": "havi.video_publish"},
        "havi.content.*": {"queue": "havi.content"},
        "havi.publish.*": {"queue": "havi.publish"},
        "havi.inbox.*": {"queue": "havi.inbox"},
    },
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
)
