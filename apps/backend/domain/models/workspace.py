"""Workspace, thành viên và brand profile — xem docs/architecture/TECHNICAL_SPEC.md §1-2."""

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import Industry, InvoiceStatus, Plan, PublishMode, WorkspaceRole
from domain.models.base import Base, CreatedAtMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin


class Workspace(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "workspaces"

    name: Mapped[str]
    industry: Mapped[Industry] = mapped_column(Enum(Industry, native_enum=False))
    plan: Mapped[Plan] = mapped_column(Enum(Plan, native_enum=False), default=Plan.TRIAL)
    publish_mode: Mapped[PublishMode] = mapped_column(
        Enum(PublishMode, native_enum=False), default=PublishMode.REVIEW_FIRST
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    # --- Gói cước ------------------------------------------------------------
    #
    # Chỉ lưu hai MỐC THỜI GIAN, không lưu `status`: trạng thái là hàm của thời
    # gian nên lưu nó là lưu một bản sao sai ngay khi đồng hồ nhích qua mốc. Xem
    # `domain/policies/subscription.state_for`.
    #
    # NULL ở `trial_ends_at` là dữ liệu có trước cột này và được coi là còn dùng
    # thử — không khoá tài khoản của người đang dùng thật chỉ vì thiếu dữ liệu.
    trial_ends_at: Mapped[datetime | None] = mapped_column(default=None)
    #: Mốc hết kỳ đã trả tiền. NULL với workspace chưa trả lần nào.
    paid_until: Mapped[datetime | None] = mapped_column(default=None)


class WorkspaceMember(CreatedAtMixin, Base):
    """1 user có thể thuộc nhiều workspace — mọi query nghiệp vụ scope theo workspace_id."""

    __tablename__ = "workspace_members"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[WorkspaceRole] = mapped_column(Enum(WorkspaceRole, native_enum=False))


class Invoice(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Một lần đổi gói ghi ra một hoá đơn.

    Bảng riêng chứ không suy từ `event_log`: hoá đơn là chứng từ tiền bạc chủ
    tiệm có quyền tra lại, còn `event_log` là dữ liệu vận hành có thể bị cắt bớt
    theo thời gian giữ. Hai vòng đời khác nhau thì không dùng chung một bảng.

    `amount_vnd` được chốt tại thời điểm phát hành và KHÔNG đọc lại từ
    `MONTHLY_PRICE_VND`: đổi bảng giá sau này không được phép sửa lại số tiền
    trên hoá đơn đã phát.
    """

    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_workspace_issued", "workspace_id", "issued_at"),
        UniqueConstraint(
            "gateway_reference", name="uq_invoices_gateway_reference"
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    plan: Mapped[Plan] = mapped_column(Enum(Plan, native_enum=False))
    amount_vnd: Mapped[int]
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, native_enum=False), default=InvoiceStatus.PENDING
    )
    issued_at: Mapped[datetime]
    #: Mã tham chiếu duy nhất từ cổng thanh toán; NULL khi chưa thanh toán.
    gateway_reference: Mapped[str | None] = mapped_column(default=None)


class BrandProfile(UpdatedAtMixin, Base):
    """Input bắt buộc cho mọi prompt chế bản — 1:1 với workspace."""

    __tablename__ = "brand_profiles"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    industry: Mapped[Industry] = mapped_column(Enum(Industry, native_enum=False))
    tone: Mapped[str] = mapped_column(default="")
    banned_claims: Mapped[list[str]] = mapped_column(JSONB, default=list)
    faq: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    logo_url: Mapped[str | None] = mapped_column(default=None)
    brand_colors: Mapped[list[str]] = mapped_column(JSONB, default=list)
