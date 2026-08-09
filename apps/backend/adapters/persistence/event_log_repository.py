"""Ghi event_log vào Postgres.

`core/events.py` giữ `EventLogEntry` làm contract và chỉ log ra stdout — nó không
được import SQLAlchemy (domain không phụ thuộc framework, xem
SYSTEM_ARCHITECTURE.md §0). Repository này là chỗ duy nhất thực sự insert.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.events import EventLogEntry, record_event
from domain.models.audit import EventLog


class EventLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, entry: EventLogEntry) -> EventLog:
        # Log ra stdout luôn: nếu transaction rollback vì lỗi sau đó, ít nhất vẫn
        # còn dấu vết trong log để debug.
        record_event(entry)
        row = EventLog(
            workspace_id=entry.workspace_id,
            job_id=entry.job_id,
            job_kind=entry.job_kind,
            input_summary=entry.input_summary,
            output_summary=entry.output_summary,
            tokens_in=entry.tokens_in,
            tokens_out=entry.tokens_out,
            duration_ms=entry.duration_ms,
            provider=entry.provider,
            error=entry.error,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def tokens_used_since(self, *, workspace_id: UUID, since: datetime) -> int:
        """Tổng token (in + out) của workspace từ `since`.

        Cộng gộp `tokens_in` và `tokens_out` thành một số vì quota tính theo
        token, không theo tiền — không cần biết đơn giá của provider nào, và số
        token là sự thật tuyệt đối trong `event_log` chứ không phụ thuộc bảng giá
        có thể lạc hậu.

        Đếm cả dòng có `error`: provider trả lỗi vẫn tốn token đã gửi. Bỏ chúng ra
        là mở đường cho một workspace liên tục gửi prompt lỗi mà không tính vào
        quota.
        """
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(EventLog.tokens_in + EventLog.tokens_out), 0)
            ).where(
                EventLog.workspace_id == workspace_id, EventLog.created_at >= since
            )
        )
        return int(result.scalar() or 0)

    async def list_for_workspace(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID | None = None,
        job_kind: str | None = None,
        provider: str | None = None,
        error_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EventLog], int]:
        """Tra event log đã scope theo workspace.

        Đây là query hỗ trợ vận hành, không phải analytics public. Chỉ lọc trên
        cột có cấu trúc (`job_id`, `job_kind`, `provider`, `error`), tránh parse
        `input_summary`/`output_summary` tự do rồi tạo cảm giác tìm kiếm chính
        xác trong khi thực ra phụ thuộc format câu chữ.
        """
        filters = [EventLog.workspace_id == workspace_id]
        if job_id is not None:
            filters.append(EventLog.job_id == job_id)
        if job_kind is not None:
            filters.append(EventLog.job_kind == job_kind)
        if provider is not None:
            filters.append(EventLog.provider == provider)
        if error_only:
            filters.append(EventLog.error.is_not(None))

        total = await self._session.execute(select(func.count()).where(*filters))
        rows = await self._session.execute(
            select(EventLog)
            .where(*filters)
            .order_by(EventLog.created_at.desc(), EventLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total.scalar_one()
