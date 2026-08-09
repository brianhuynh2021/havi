"""event_log — bảng thật cho core.events.EventLogEntry (đang log ra stdout tạm)."""

import uuid

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class EventLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "event_log"
    __table_args__ = (Index("ix_event_log_workspace_created", "workspace_id", "created_at"),)

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(index=True, default=None)
    job_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    job_kind: Mapped[str]
    input_summary: Mapped[str] = mapped_column(default="")
    output_summary: Mapped[str] = mapped_column(default="")
    tokens_in: Mapped[int] = mapped_column(default=0)
    tokens_out: Mapped[int] = mapped_column(default=0)
    # Provider nào phục vụ lượt này. Cột riêng chứ không nhét trong
    # `output_summary`: cần lọc/GROUP BY được để trả lời "provider nào đang hỏng"
    # hay "bài này do model nào sinh", mà parse chuỗi tự do trong SQL thì mỗi câu
    # query một kiểu và sai âm thầm. Nullable cho dòng cũ ghi trước khi có cột này.
    #
    # Quota KHÔNG dùng cột này: Havi chặn theo *token*, không theo tiền, nên
    # không cần đơn giá của từng provider (xem `domain/policies/quota.py`).
    provider: Mapped[str | None] = mapped_column(default=None)
    duration_ms: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(default=None)
