"""Port mỏng cho việc đẩy job vào hàng đợi.

Có lớp này để router không import Celery trực tiếp: test override được bằng một
implementation thu-vào-list, thay vì phải dựng Redis + worker chỉ để kiểm router
có enqueue đúng hay không. (Celery `task_always_eager` không giải quyết được ở đây
vì task tạo DB session riêng, không thấy transaction mà test đang rollback.)
"""

from abc import ABC, abstractmethod
from uuid import UUID


class JobQueue(ABC):
    @abstractmethod
    def enqueue_generate_drafts(
        self, *, workspace_id: UUID, job_id: UUID, request_id: str | None = None
    ) -> None: ...

    @abstractmethod
    def enqueue_webhook_payload(
        self, *, payload: dict, request_id: str | None = None
    ) -> None: ...


class CeleryJobQueue(JobQueue):
    def enqueue_generate_drafts(
        self, *, workspace_id: UUID, job_id: UUID, request_id: str | None = None
    ) -> None:
        # Import trong hàm: API process không cần Celery đã cài để khởi động được
        # (extra `queue` là optional dependency).
        from worker.tasks import generate_drafts

        generate_drafts.delay(
            workspace_id=str(workspace_id), job_id=str(job_id), request_id=request_id
        )

    def enqueue_webhook_payload(
        self, *, payload: dict, request_id: str | None = None
    ) -> None:
        from worker.tasks import process_webhook_payload

        process_webhook_payload.delay(payload=payload, request_id=request_id)


class RecordingJobQueue(JobQueue):
    """Dùng trong test — ghi lại lời gọi thay vì đẩy vào Redis thật."""

    def __init__(self) -> None:
        self.enqueued: list[tuple[UUID, UUID, str | None]] = []
        self.enqueued_webhooks: list[tuple[dict, str | None]] = []

    def enqueue_generate_drafts(
        self, *, workspace_id: UUID, job_id: UUID, request_id: str | None = None
    ) -> None:
        self.enqueued.append((workspace_id, job_id, request_id))

    def enqueue_webhook_payload(
        self, *, payload: dict, request_id: str | None = None
    ) -> None:
        self.enqueued_webhooks.append((payload, request_id))
