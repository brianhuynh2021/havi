"""SQLAlchemy model cho InboxItem — xem docs/architecture/TECHNICAL_SPEC.md §8."""

import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import InboxItemStatus, InboxItemType, Platform
from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class InboxItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "inbox_items"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id"), index=True
    )
    platform: Mapped[Platform] = mapped_column(Enum(Platform, native_enum=False))
    type: Mapped[InboxItemType] = mapped_column(
        Enum(InboxItemType, native_enum=False), default=InboxItemType.MESSAGE
    )
    content: Mapped[str]
    author_name: Mapped[str]
    sentiment: Mapped[str | None] = mapped_column(default=None)
    ai_suggested_reply: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[InboxItemStatus] = mapped_column(
        Enum(InboxItemStatus, native_enum=False), default=InboxItemStatus.NEW
    )
