"""event_log — mọi job ghi lại input/output/token/thời gian.

Mục tiêu vận hành: debug 1 dòng, tính tiền 1 query. Chưa nối DB nên tạm log ra stdout;
khi có Postgres thì thay `record_event` bằng insert vào bảng `event_log`.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger("havi.event_log")


class EventLogEntry(BaseModel):
    workspace_id: UUID | None = None
    job_id: UUID | None = None
    job_kind: str
    input_summary: str = ""
    output_summary: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def record_event(entry: EventLogEntry) -> None:
    # TODO(db): insert vào bảng event_log thay vì log ra stdout.
    logger.info("event_log %s", entry.model_dump_json())
