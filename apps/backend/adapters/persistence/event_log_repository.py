"""Ghi event_log vào Postgres.

`core/events.py` giữ `EventLogEntry` làm contract và chỉ log ra stdout — nó không
được import SQLAlchemy (domain không phụ thuộc framework, xem
SYSTEM_ARCHITECTURE.md §0). Repository này là chỗ duy nhất thực sự insert.
"""

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
            error=entry.error,
        )
        self._session.add(row)
        await self._session.flush()
        return row
