"""SQLAlchemy model cho InboxItem — xem docs/architecture/TECHNICAL_SPEC.md §8."""

import uuid

from sqlalchemy import Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import InboxItemStatus, InboxItemType, Platform
from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class InboxItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "inbox_items"

    #: Chống trùng khi nền tảng gửi lại webhook. Meta retry cùng một sự kiện khi
    #: không nhận được 200 kịp, nên "đã xử lý chưa" phải là ràng buộc ở Postgres
    #: chứ không phải một lần SELECT trước INSERT — hai worker chạy song song thì
    #: SELECT của cả hai đều trả rỗng.
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "platform",
            "external_message_id",
            name="uq_inbox_items_external_message",
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    #: ID sự kiện do nền tảng cấp. NULL cho item tạo tay/seed — Postgres coi mỗi
    #: NULL là khác nhau nên unique constraint không chặn các item đó.
    external_message_id: Mapped[str | None] = mapped_column(default=None)
    #: ID người gửi trên nền tảng (PSID với Facebook Messenger) để gửi trả lời trực tiếp.
    recipient_id: Mapped[str | None] = mapped_column(default=None)
    platform: Mapped[Platform] = mapped_column(Enum(Platform, native_enum=False))
    type: Mapped[InboxItemType] = mapped_column(
        Enum(InboxItemType, native_enum=False), default=InboxItemType.MESSAGE
    )
    content: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str]
    sentiment: Mapped[str | None] = mapped_column(default=None)
    ai_suggested_reply: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[InboxItemStatus] = mapped_column(
        Enum(InboxItemStatus, native_enum=False), default=InboxItemStatus.NEW
    )
