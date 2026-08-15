"""SQLAlchemy model cho CrmNudge — lưu trữ tin nhắn chăm sóc khách hàng định kỳ."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import CrmMessageStatus, CrmNudgeType
from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class CrmNudge(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "crm_nudges"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    nudge_type: Mapped[CrmNudgeType] = mapped_column(
        Enum(CrmNudgeType, native_enum=False), default=CrmNudgeType.INACTIVE_30_DAYS
    )
    status: Mapped[CrmMessageStatus] = mapped_column(
        Enum(CrmMessageStatus, native_enum=False),
        default=CrmMessageStatus.PENDING_APPROVAL,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
