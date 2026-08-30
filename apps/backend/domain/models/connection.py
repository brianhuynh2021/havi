"""Kết nối OAuth tới nền tảng đăng bài — xem docs/architecture/TECHNICAL_SPEC.md §4."""

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import ConnectionStatus, Platform
from domain.models.base import Base, CreatedAtMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin


class PlatformConnection(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    """Token đăng bài của một workspace trên một nền tảng.

    Token nằm ở dạng đã mã hoá (`core.token_crypto`) — cột này không bao giờ
    được đưa vào response, kể cả response nội bộ. Repository trả về model thì
    router phải map sang `core.schemas.PlatformConnection`, và schema đó cố ý
    không có field token.
    """

    __tablename__ = "platform_connections"
    __table_args__ = (
        # Một workspace chỉ có một kết nối cho mỗi nền tảng. Nối lại thì cập
        # nhật bản ghi cũ chứ không tạo bản ghi thứ hai — nếu không, lúc publish
        # sẽ không biết token nào là token còn hiệu lực.
        UniqueConstraint("workspace_id", "platform", name="uq_connection_workspace_platform"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform, native_enum=False))
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus, native_enum=False), default=ConnectionStatus.CONNECTED
    )

    # --- Token (đã mã hoá) ---------------------------------------------------
    access_token_encrypted: Mapped[str]
    # Facebook Page token dài hạn không có refresh token; Google thì có. Nullable
    # để không ép nền tảng nào cũng phải có.
    refresh_token_encrypted: Mapped[str | None] = mapped_column(default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # --- Thông tin hiển thị --------------------------------------------------
    # Tên Page/OA để chủ tiệm nhận ra mình đang nối đúng trang nào. Không phải
    # dữ liệu nhạy cảm nên lưu thẳng.
    account_name: Mapped[str | None] = mapped_column(default=None)
    # ID của Page trên nền tảng — cần khi gọi API đăng bài.
    external_account_id: Mapped[str | None] = mapped_column(default=None)
    # App-scoped ID của người đã cấp OAuth. Chỉ dùng để xử lý Meta Data Deletion
    # Request có chữ ký; không đưa ra API/UI và không dùng làm danh tính Havi.
    external_user_id: Mapped[str | None] = mapped_column(index=True, default=None)
    connected_by: Mapped[uuid.UUID | None] = mapped_column(default=None)

    # Lý do mất kết nối (token hết hạn, chủ tiệm gỡ quyền ở phía Facebook…), để
    # UI nói được vì sao phải nối lại thay vì chỉ hiện chấm đỏ.
    failure_reason: Mapped[str | None] = mapped_column(default=None)

    # Quyền nền tảng thực sự cấp lúc nối. NULL = kết nối cũ nối trước khi có cột
    # này, tức là **không rõ** — chỗ đọc phải cho phép thử chứ không được coi là
    # "không có quyền nào", nếu không mọi kết nối cũ mất sạch tính năng.
    granted_scopes: Mapped[list[str] | None] = mapped_column(
        ARRAY(String()), default=None
    )
