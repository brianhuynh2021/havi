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
    duration_ms: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(default=None)
