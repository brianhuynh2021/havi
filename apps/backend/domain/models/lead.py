"""SQLAlchemy model cho Lead và CrmMessage — xem docs/architecture/TECHNICAL_SPEC.md §8."""

import uuid

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import LeadReplyStatus, LeadSource, LeadStage
from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Lead(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "leads"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str]
    phone: Mapped[str | None] = mapped_column(default=None)
    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource, native_enum=False), default=LeadSource.FANPAGE
    )
    stage: Mapped[LeadStage] = mapped_column(
        Enum(LeadStage, native_enum=False), default=LeadStage.NEW
    )
    reply_status: Mapped[LeadReplyStatus] = mapped_column(
        Enum(LeadReplyStatus, native_enum=False), default=LeadReplyStatus.NEW
    )
    # Text chứ không String: tin nhắn khách và ghi chú của chủ tiệm không có
    # trần độ dài hợp lý nào, và migration đã tạo cột là TEXT — model phải
    # khớp, nếu không `alembic check` báo drift mãi.
    message: Mapped[str | None] = mapped_column(Text, default=None)
    suggested_reply: Mapped[str | None] = mapped_column(Text, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
