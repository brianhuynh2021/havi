"""Đọc outbox → đẩy vào Celery. Chạy định kỳ trong Celery Beat.

Đây là nửa sau của Transactional Outbox: `OutboxJobQueue` ghi việc vào DB cùng
transaction nghiệp vụ, dispatcher này mới thực sự gọi Redis.

Thứ tự trong `_dispatch_one` là điểm mấu chốt và **không được đổi**:

    1. gọi Celery
    2. đánh dấu `dispatched`

Đảo lại (đánh dấu trước, gọi sau) thì process chết ở giữa sẽ để lại một bản ghi
mang nhãn "đã đẩy" mà không ai nhận — chính là mất việc, đúng thứ Outbox sinh ra
để chống. Giữ đúng thứ tự này thì trường hợp xấu nhất là *đẩy hai lần*, và
`idempotency_key` ở tầng DB đã lo phần đó.
"""

import logging
from datetime import UTC, datetime, timedelta

from adapters.persistence.outbox_repository import OutboxRepository
from core.metrics import outbox_dispatched_total, outbox_pending
from core.structured_logging import log_json
from domain.models.outbox import OutboxEntry

logger = logging.getLogger("havi.outbox_dispatcher")

#: Allow-list tường minh: topic → hàm đẩy task.
#:
#: Không `getattr(worker.tasks, topic)`: `topic` đi từ DB, và một bảng có thể sửa
#: được (hoặc một bug ghi sai) sẽ trở thành đường gọi hàm tuỳ ý trong process
#: worker. Dict tường minh nghĩa là chỉ những task ở đây mới gọi được, và thêm
#: task mới là một thay đổi code có review.
#:
#: Giữ ở cấp module dưới dạng tên chuỗi, resolve lúc gọi: import `worker.tasks`
#: ở đầu file sẽ buộc API process phải có Celery mới khởi động được.
_TOPICS: dict[str, str] = {
    "generate_drafts": "generate_drafts",
    "process_webhook_payload": "process_webhook_payload",
}


class UnknownTopicError(Exception):
    pass


def _send_to_celery(topic: str, payload: dict) -> None:
    task_name = _TOPICS.get(topic)
    if task_name is None:
        raise UnknownTopicError(f"topic '{topic}' không có trong allow-list")
    from worker import tasks

    getattr(tasks, task_name).delay(**payload)


class OutboxDispatcher:
    def __init__(self, outbox: OutboxRepository) -> None:
        self._outbox = outbox

    async def run_once(self, *, limit: int = 50, max_batches: int = 5) -> dict:
        """Một lượt: nhận lô, đẩy từng cái, cập nhật số liệu.

        Lặp tối đa `max_batches` nếu còn việc để giải phóng hàng đợi nhanh trong một chu kỳ beat.
        """
        total_dispatched = 0
        total_failed = 0

        for _ in range(max_batches):
            entries = await self._outbox.claim_batch(limit=limit)
            if not entries:
                break
            for entry in entries:
                if await self._dispatch_one(entry):
                    total_dispatched += 1
                else:
                    total_failed += 1
            if len(entries) < limit:
                break

        # Đo *sau* khi xử lý: đây là tồn đọng còn lại, con số dùng để đặt alert.
        pending = await self._outbox.pending_count()
        outbox_pending.set(pending)

        if total_dispatched or total_failed:
            log_json(
                logger,
                logging.INFO,
                "outbox.run",
                dispatched=total_dispatched,
                failed=total_failed,
                pending=pending,
            )
        return {"dispatched": total_dispatched, "failed": total_failed, "pending": pending}

    async def _dispatch_one(self, entry: OutboxEntry) -> bool:
        try:
            _send_to_celery(entry.topic, entry.payload)
        except UnknownTopicError as exc:
            # Lỗi vĩnh viễn: thử lại bao nhiêu lần cũng vậy. Đốt hết lượt thử
            # ngay để nó vào `failed` và hiện ra cho người xem, thay vì lặng lẽ
            # thử lại 8 lần trong 4 phút rồi mới báo.
            entry.attempts = 999
            await self._outbox.mark_retry(entry, error=str(exc))
            outbox_dispatched_total.labels(outcome="unknown_topic").inc()
            return False
        except Exception as exc:
            await self._outbox.mark_retry(entry, error=f"{type(exc).__name__}: {exc}")
            outbox_dispatched_total.labels(outcome="error").inc()
            logger.warning("outbox %s đẩy thất bại: %s", entry.id, exc)
            return False

        await self._outbox.mark_dispatched(entry)
        outbox_dispatched_total.labels(outcome="ok").inc()
        return True

    async def purge_old(self, *, older_than_days: int = 7) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
        return await self._outbox.purge_dispatched_before(cutoff=cutoff)
