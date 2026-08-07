"""Workspace, thành viên và brand profile — xem docs/architecture/TECHNICAL_SPEC.md §1-2."""

import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import Industry, Plan, PublishMode, WorkspaceRole
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


class WorkspaceMember(CreatedAtMixin, Base):
    """1 user có thể thuộc nhiều workspace — mọi query nghiệp vụ scope theo workspace_id."""

    __tablename__ = "workspace_members"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[WorkspaceRole] = mapped_column(Enum(WorkspaceRole, native_enum=False))


class BrandProfile(UpdatedAtMixin, Base):
    """Input bắt buộc cho mọi prompt chế bản — 1:1 với workspace."""

    __tablename__ = "brand_profiles"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id"), primary_key=True
    )
    industry: Mapped[Industry] = mapped_column(Enum(Industry, native_enum=False))
    tone: Mapped[str] = mapped_column(default="")
    banned_claims: Mapped[list[str]] = mapped_column(JSONB, default=list)
    faq: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    logo_url: Mapped[str | None] = mapped_column(default=None)
    brand_colors: Mapped[list[str]] = mapped_column(JSONB, default=list)
