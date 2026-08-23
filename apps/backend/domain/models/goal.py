"""Goal domain model — Định nghĩa mục tiêu cốt lõi của workspace (Havi 3.0)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import GoalCategory, GoalStatus
from domain.models.base import Base, CreatedAtMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin


class Goal(Base, UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin):
    """Mục tiêu hoạt động của Workspace."""

    __tablename__ = "goals"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default=GoalCategory.ACQUIRE_CUSTOMERS.value
    )
    evidence_definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    weekly_capacity_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    constraints: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=GoalStatus.ACTIVE.value, index=True
    )
