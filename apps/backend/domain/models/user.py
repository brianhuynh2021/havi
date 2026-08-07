"""User, OTP challenge và refresh session — xem docs/architecture/TECHNICAL_SPEC.md."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "users"

    # Email là danh tính đăng nhập chính. Lý do không dùng SĐT: OTP SMS ở VN tốn
    # phí thật (~300-600đ/tin) nên ăn vào margin gói 299K/tháng, và chủ tiệm e dè
    # đưa số điện thoại vì spam. Không dùng username: thêm một thứ phải nghĩ ra và
    # dễ quên, trong khi email họ đã có sẵn và dùng lại được để khôi phục tài khoản.
    email: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    # Nullable để mở đường cho social login (Google) sau này — user đăng nhập
    # bằng OAuth thì không có password.
    password_hash: Mapped[str | None] = mapped_column(default=None)
    # Tuỳ chọn, lưu dạng +84xxxxxxxxx. KHÔNG dùng để đăng nhập — chỉ để gửi bản
    # nháp/nhắc duyệt qua Zalo OA (ROADMAP.md P1), user tự thêm trong Cài đặt.
    phone: Mapped[str | None] = mapped_column(unique=True, index=True, default=None)
    # Con trỏ UI-state (workspace đang chọn), không FK cứng — tránh circular
    # dependency users<->workspaces, và user có thể đổi workspace tự do. Tính
    # hợp lệ (user có thực sự thuộc workspace đó) enforce ở application service
    # qua workspace_members, không ở DB constraint.
    active_workspace_id: Mapped[uuid.UUID | None] = mapped_column(default=None)


class OtpChallenge(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Mã một lần gửi qua email — hiện chỉ dùng cho đặt lại mật khẩu.

    Không lưu OTP thô, chỉ lưu hash để soi log/DB không lộ mã. `attempt_count`
    chặn brute force (giới hạn ở application service); TTL và resend cooldown lấy
    từ core.config.Settings, không hardcode ở đây.

    Chưa có cột `purpose` vì hiện chỉ có một mục đích. Khi thêm mục đích thứ hai
    (xác minh email, OTP qua Zalo) thì mới thêm — không đoán trước.
    """

    __tablename__ = "otp_challenges"
    __table_args__ = (Index("ix_otp_challenges_email_expires", "email", "expires_at"),)

    email: Mapped[str] = mapped_column(index=True)
    code_hash: Mapped[str]
    expires_at: Mapped[datetime] = mapped_column()
    attempt_count: Mapped[int] = mapped_column(default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(default=None)


class RefreshSession(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Refresh token xoay vòng — lưu hash, revoke khi logout (không xoá để audit)."""

    __tablename__ = "refresh_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column()
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
