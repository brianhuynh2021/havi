"""SQLAlchemy model cho InboxItem — xem docs/architecture/TECHNICAL_SPEC.md §8."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, UniqueConstraint
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
        # Truy vấn nóng nhất của sản phẩm: màn làm việc đọc hàng đợi mỗi lần mở.
        Index("ix_inbox_items_workspace_status", "workspace_id", "status"),
        Index("ix_inbox_items_ws_status_created", "workspace_id", "status", "created_at"),
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
    #: Chữ người dùng đã gửi thực tế — tách khỏi `ai_suggested_reply` để không mất bản gợi ý gốc của AI.
    sent_reply_text: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[InboxItemStatus] = mapped_column(
        Enum(InboxItemStatus, native_enum=False), default=InboxItemStatus.NEW
    )
    #: Mốc phản hồi **đầu tiên gửi thành công**. Không dùng `updated_at` chung:
    #: sửa bản nháp hay gán lại người xử lý cũng đổi `updated_at`, và lúc đó
    #: "thời gian phản hồi" sẽ giảm dần mỗi lần có ai chạm vào tin — một chỉ số
    #: tự đẹp lên khi không ai làm gì cả.
    replied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    #: Ai đang xử lý việc này. Vuông góc với `status`: một việc có người nhận vẫn
    #: đang ở `new` cho tới khi phản hồi được gửi.
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    #: Loại việc do `domain/policies/inbox_triage.py` phân. Chuỗi tự do chứ không
    #: enum: bộ phân loại còn sửa nhiều, và enum trong Postgres đổi giá trị thì
    #: cần thêm một migration mỗi lần.
    category: Mapped[str | None] = mapped_column(default=None)
