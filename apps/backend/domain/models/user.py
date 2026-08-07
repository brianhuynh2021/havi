"""User, OTP challenge và refresh session — xem docs/architecture/TECHNICAL_SPEC.md."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "users"

    # Lưu dạng +84xxxxxxxxx (chuẩn hoá từ input 0xxxxxxxxx) — xem ROADMAP.md
    # "Việt Nam-first". Đây là danh tính đăng nhập chính; email là phụ.
    phone: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    email: Mapped[str | None] = mapped_column(unique=True, default=None)
    password_hash: Mapped[str | None] = mapped_column(default=None)
    # Con trỏ UI-state (workspace đang chọn), không FK cứng — tránh circular
    # dependency users<->workspaces, và user có thể đổi workspace tự do. Tính
    # hợp lệ (user có thực sự thuộc workspace đó) enforce ở application service
    # qua workspace_members, không ở DB constraint.
    active_workspace_id: Mapped[uuid.UUID | None] = mapped_column(default=None)


class OtpChallenge(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Không lưu OTP thô — chỉ lưu hash để soi log/DB không lộ mã.

    `attempt_count` chặn brute force (giới hạn ở application service); TTL và
    resend cooldown lấy từ core.config.Settings, không hardcode ở đây.
    """

    __tablename__ = "otp_challenges"
    __table_args__ = (Index("ix_otp_challenges_phone_expires", "phone", "expires_at"),)

    phone: Mapped[str] = mapped_column(index=True)
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
