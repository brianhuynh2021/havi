"""video_render_jobs — Quản lý hàng đợi render video tự động (Phase 3 Video Pipeline).

Xem docs/architecture/VIDEO_PIPELINE.md.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import VideoRenderEngine, VideoRenderStatus
from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class VideoRenderJob(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "video_render_jobs"
    __table_args__ = (
        Index("ix_video_render_jobs_workspace_status", "workspace_id", "status"),
        Index("ix_video_render_jobs_created_at", "created_at"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    title: Mapped[str] = mapped_column(default="Video ngắn tự động")
    target_aspect_ratio: Mapped[str] = mapped_column(default="9:16")
    status: Mapped[VideoRenderStatus] = mapped_column(
        Enum(VideoRenderStatus, native_enum=False), default=VideoRenderStatus.QUEUED
    )
    progress_percent: Mapped[int] = mapped_column(default=0)
    renderer_engine: Mapped[VideoRenderEngine] = mapped_column(
        Enum(VideoRenderEngine, native_enum=False), default=VideoRenderEngine.FFMPEG
    )

    source_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id"), default=None, nullable=True
    )
    edit_plan: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    output_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id"), default=None, nullable=True
    )
    output_url: Mapped[str | None] = mapped_column(default=None, nullable=True)
    error_message: Mapped[str | None] = mapped_column(default=None, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(default=None, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(default=None, nullable=True)
