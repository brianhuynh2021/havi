"""Port mỏng cho việc đẩy job vào hàng đợi.

Có lớp này để router không import Celery trực tiếp: test override được bằng một
implementation thu-vào-list, thay vì phải dựng Redis + worker chỉ để kiểm router
có enqueue đúng hay không. (Celery `task_always_eager` không giải quyết được ở đây
vì task tạo DB session riêng, không thấy transaction mà test đang rollback.)
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from adapters.persistence.outbox_repository import OutboxRepository


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


class OutboxJobQueue(JobQueue):
    """JobQueue ghi vào bảng `outbox` thay vì gọi Redis ngay.

    Đây là bản dùng ở production. Nó giữ đúng interface `JobQueue` nên không chỗ
    gọi nào phải sửa — cái thay đổi là *thời điểm* việc đó tới Redis: sau khi
    transaction commit, do `OutboxDispatcher` đẩy.

    Vì sao vẫn đồng bộ (không `async`) dù có ghi DB: `session.add()` không đi
    mạng, nó chỉ đặt object vào bộ nhớ của session. Đổi signature thành async sẽ
    buộc sửa mọi caller mà chẳng đổi được gì về hành vi.

    Đánh đổi cần biết: job **không** còn tới worker tức thì, mà trễ tối đa một
    chu kỳ dispatcher (xem `scheduler/beat.py`). Với Havi thì đây là đánh đổi
    đúng: bài đăng đã có lịch tính theo phút, còn mất job là mất niềm tin.
    """

    def __init__(self, outbox: "OutboxRepository") -> None:  # noqa: F821
        self._outbox = outbox

    def enqueue_generate_drafts(
        self, *, workspace_id: UUID, job_id: UUID, request_id: str | None = None
    ) -> None:
        self._outbox.enqueue(
            topic="generate_drafts",
            # Chuỗi hoá UUID tại đây: payload đi vào JSONB, và `json.dumps` không
            # xử lý được UUID. Để lộ lỗi này ra lúc dispatch thì nó xảy ra trong
            # worker nền, xa chỗ gây ra và khó truy hơn nhiều.
            payload={
                "workspace_id": str(workspace_id),
                "job_id": str(job_id),
                "request_id": request_id,
            },
            request_id=request_id,
            workspace_id=workspace_id,
        )

    def enqueue_webhook_payload(
        self, *, payload: dict, request_id: str | None = None
    ) -> None:
        self._outbox.enqueue(
            topic="process_webhook_payload",
            payload={"payload": payload, "request_id": request_id},
            request_id=request_id,
        )
