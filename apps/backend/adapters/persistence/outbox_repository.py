"""Đọc/ghi bảng outbox.

`enqueue` cố ý **không** commit: nó chỉ `add` vào session đang mở, để bản ghi
outbox commit *cùng* transaction với dữ liệu nghiệp vụ đã sinh ra nó. Đó là toàn
bộ lý do Outbox tồn tại — commit riêng ở đây thì lại thành dual-write, đúng thứ
vừa đi vá.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import OutboxStatus
from domain.models.outbox import OutboxEntry

logger = logging.getLogger("havi.outbox")

#: Số lần thử trước khi bỏ vào `failed`. 8 lần với backoff dưới đây ≈ hơn 4 phút
#: kiên trì — đủ để Redis restart xong, chưa tới mức giữ rác cả ngày.
MAX_ATTEMPTS = 8

#: Backoff mũ có trần. Trần 60s để một outage dài không đẩy lần thử kế tiếp ra xa
#: hàng giờ: lúc Redis sống lại, việc tồn đọng phải chạy trong vòng một phút.
_BASE_BACKOFF_SECONDS = 2
_MAX_BACKOFF_SECONDS = 60


def _backoff(attempts: int) -> timedelta:
    seconds = min(_BASE_BACKOFF_SECONDS**attempts, _MAX_BACKOFF_SECONDS)
    return timedelta(seconds=seconds)


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def enqueue(
        self,
        *,
        topic: str,
        payload: dict,
        request_id: str | None = None,
        workspace_id: UUID | None = None,
    ) -> OutboxEntry:
        """Thêm việc vào outbox trong transaction hiện tại.

        Đồng bộ (không `async`) và không `flush`: nó chỉ đặt object vào session.
        Ai gọi thì đã ở trong một transaction, và chính transaction đó quyết định
        bản ghi này có tồn tại hay không.
        """
        entry = OutboxEntry(
            topic=topic,
            payload=payload,
            status=OutboxStatus.PENDING,
            available_at=datetime.now(UTC),
            request_id=request_id,
            workspace_id=workspace_id,
        )
        self._session.add(entry)
        return entry

    async def claim_batch(self, *, limit: int = 50) -> list[OutboxEntry]:
        """Nhận một lô việc chờ, khoá chúng lại cho dispatcher này.

        `FOR UPDATE SKIP LOCKED` là mấu chốt để chạy nhiều dispatcher song song:
        mỗi tiến trình khoá phần của mình và **bỏ qua** dòng tiến trình khác đang
        giữ, thay vì xếp hàng chờ. Không có `SKIP LOCKED` thì dispatcher thứ hai
        block trên cùng dòng đầu tiên và song song hoá thành vô nghĩa.

        Không có trạng thái `processing` trong bảng: row lock đã là cơ chế giữ
        chỗ, và lock tự nhả nếu tiến trình chết — một cột trạng thái thì không.
        """
        result = await self._session.execute(
            select(OutboxEntry)
            .where(
                OutboxEntry.status == OutboxStatus.PENDING,
                OutboxEntry.available_at <= datetime.now(UTC),
            )
            .order_by(OutboxEntry.available_at, OutboxEntry.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def mark_dispatched(self, entry: OutboxEntry) -> None:
        entry.status = OutboxStatus.DISPATCHED
        entry.dispatched_at = datetime.now(UTC)
        entry.last_error = None
        await self._session.flush()

    async def mark_retry(self, entry: OutboxEntry, *, error: str) -> None:
        """Tăng số lần thử, giãn `available_at`, hoặc bỏ vào `failed` khi hết lượt."""
        entry.attempts += 1
        # Cắt ngắn: `last_error` để người vận hành đọc, không phải để lưu trace.
        # Một traceback đầy đủ nhân với vài nghìn dòng làm phình bảng vô ích.
        entry.last_error = error[:500]
        if entry.attempts >= MAX_ATTEMPTS:
            entry.status = OutboxStatus.FAILED
            logger.error(
                "outbox entry %s bỏ sau %d lần thử: %s", entry.id, entry.attempts, error
            )
        else:
            entry.available_at = datetime.now(UTC) + _backoff(entry.attempts)
        await self._session.flush()

    async def pending_count(self) -> int:
        result = await self._session.execute(
            select(func.count()).where(OutboxEntry.status == OutboxStatus.PENDING)
        )
        return int(result.scalar_one())

    async def failed_count(self) -> int:
        result = await self._session.execute(
            select(func.count()).where(OutboxEntry.status == OutboxStatus.FAILED)
        )
        return int(result.scalar_one())

    async def requeue_failed(self, *, limit: int = 100) -> int:
        """Đưa các dòng `failed` về `pending` — cho vận hành sau khi đã sửa gốc.

        Có hàm này để không ai phải `UPDATE` bảng bằng tay ở production, thao tác
        vừa dễ sai vừa không để lại dấu.
        """
        result = await self._session.execute(
            update(OutboxEntry)
            .where(
                OutboxEntry.id.in_(
                    select(OutboxEntry.id)
                    .where(OutboxEntry.status == OutboxStatus.FAILED)
                    .limit(limit)
                )
            )
            .values(
                status=OutboxStatus.PENDING,
                attempts=0,
                available_at=datetime.now(UTC),
                last_error=None,
            )
        )
        await self._session.flush()
        return int(result.rowcount or 0)

    async def purge_dispatched_before(self, *, cutoff: datetime) -> int:
        """Dọn lịch sử đã đẩy. Outbox là hàng đợi, không phải audit log —
        `event_log` mới là chỗ giữ lịch sử, và nó bất biến."""
        from sqlalchemy import delete

        result = await self._session.execute(
            delete(OutboxEntry).where(
                OutboxEntry.status == OutboxStatus.DISPATCHED,
                OutboxEntry.dispatched_at < cutoff,
            )
        )
        await self._session.flush()
        return int(result.rowcount or 0)

    async def list_entries(
        self,
        *,
        workspace_id: UUID | None = None,
        status: OutboxStatus | None = None,
        limit: int = 50,
    ) -> list[OutboxEntry]:
        """Danh sách các bản ghi outbox theo workspace và status."""
        filters = []
        if workspace_id is not None:
            filters.append(OutboxEntry.workspace_id == workspace_id)
        if status is not None:
            filters.append(OutboxEntry.status == status)
        result = await self._session.execute(
            select(OutboxEntry)
            .where(*filters)
            .order_by(OutboxEntry.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
