"""event_log — mọi job ghi lại input/output/token/thời gian.

Mục tiêu vận hành: debug 1 dòng, tính tiền 1 query.

`EventLogEntry` là contract; `record_event` chỉ log ra stdout. Việc insert vào
bảng `event_log` nằm ở `adapters/persistence/event_log_repository.py` — file này
không được import SQLAlchemy (domain không phụ thuộc framework, xem
SYSTEM_ARCHITECTURE.md §0).
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger("havi.event_log")


class EventLogEntry(BaseModel):
    workspace_id: UUID | None = None
    job_id: UUID | None = None
    request_id: str | None = None
    job_kind: str
    input_summary: str = ""
    output_summary: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0
    #: Provider phục vụ lượt này (`gemini`/`anthropic`/`openai`). Cần cho việc
    #: tính tiền vì mỗi provider một đơn giá — xem `domain/policies/pricing.py`.
    provider: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def record_event(entry: EventLogEntry) -> None:
    """Log ra stdout. Muốn lưu vào DB thì dùng `EventLogRepository.record`."""
    logger.info("event_log %s", entry.model_dump_json())
