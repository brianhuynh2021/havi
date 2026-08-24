"""Roadmap, RoadmapTask, EvidenceLog, RoadmapReview domain models (Havi 3.0)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import ReviewDecision, RoadmapStatus, TaskOwnerType, TaskStatus
from domain.models.base import Base, CreatedAtMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin


class Roadmap(Base, UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin):
    """Lộ trình thực hiện mục tiêu đa chân trời (90d / 30d / 7d / Hôm nay)."""

    __tablename__ = "roadmaps"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    horizon_90d: Mapped[str] = mapped_column(Text, nullable=False, default="")
    horizon_30d: Mapped[str] = mapped_column(Text, nullable=False, default="")
    horizon_7d: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assumptions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RoadmapStatus.ACTIVE.value, index=True
    )


class RoadmapTask(Base, UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin):
    """Nhiệm vụ cụ thể nằm trong lộ trình."""

    __tablename__ = "roadmap_tasks"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_this_is_next: Mapped[str] = mapped_column(Text, nullable=False, default="")
    time_estimate_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    owner_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TaskOwnerType.COLLABORATIVE.value
    )
    capability_module: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    inputs_needed: Mapped[str | None] = mapped_column(Text, nullable=True)
    done_rule: Mapped[str] = mapped_column(Text, nullable=False, default="")
    fallback_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TaskStatus.PENDING.value, index=True
    )
    scheduled_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class EvidenceLog(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Bằng chứng kết quả thực tế (Verified Evidence) gắn với mục tiêu & nhiệm vụ."""

    __tablename__ = "evidence_logs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("roadmap_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual_checkin")
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False, default="note")
    value_number: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str] = mapped_column(Text, nullable=False)
    media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class RoadmapReview(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Đánh giá hàng tuần & đề xuất cập nhật lộ trình (Weekly Review & Replan)."""

    __tablename__ = "roadmap_reviews"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    review_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    completed_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    obstacles_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decision: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReviewDecision.CONTINUE.value
    )
    replan_diff: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
