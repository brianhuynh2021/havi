"""content_jobs / content_items / content_item_versions — xem TECHNICAL_SPEC §5.

Một content job = một lần gọi LLM, sinh nhiều content item theo kênh (nguyên tắc
#5 ở ROADMAP.md §1). Sửa text tạo version mới, không ghi đè bản cũ.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import Channel, ContentJobStatus, ContentStatus
from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ContentJob(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "content_jobs"
    __table_args__ = (
        # Cùng một idempotency key trong một workspace chỉ tạo được một job —
        # bấm "Để Havi viết cho chị" hai lần không tốn hai lần tiền LLM.
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_content_jobs_idempotency"),
        Index("ix_content_jobs_workspace_status", "workspace_id", "status"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    status: Mapped[ContentJobStatus] = mapped_column(
        Enum(ContentJobStatus, native_enum=False), default=ContentJobStatus.QUEUED
    )
    # Lưu nguyên payload raw_inputs để trace lại được job đã nhận gì.
    raw_inputs: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    idempotency_key: Mapped[str]
    failure_reason: Mapped[str | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class ContentItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "content_items"
    __table_args__ = (
        Index("ix_content_items_workspace_status", "workspace_id", "status"),
        Index("ix_content_items_workspace_scheduled", "workspace_id", "scheduled_at"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_jobs.id"), index=True, default=None
    )
    channel: Mapped[Channel] = mapped_column(Enum(Channel, native_enum=False))
    kind: Mapped[str]
    text: Mapped[str]
    media_note: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, native_enum=False), default=ContentStatus.PENDING_APPROVAL
    )
    version_no: Mapped[int] = mapped_column(default=1)
    # timezone=True bắt buộc: sản phẩm chạy ở Asia/Ho_Chi_Minh nhưng lưu UTC. Cột
    # naive sẽ nuốt offset khi ghi datetime aware — bài hẹn 20h VN thành 20h UTC,
    # tức 3h sáng hôm sau, và không có cách nào phát hiện sau khi đã ghi.
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class ContentItemVersion(UUIDPrimaryKeyMixin, Base):
    """Lịch sử sửa — mỗi lần sửa text tạo một hàng, không update tại chỗ."""

    __tablename__ = "content_item_versions"
    __table_args__ = (
        UniqueConstraint("content_item_id", "version_no", name="uq_content_item_versions_no"),
    )

    content_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id"), index=True
    )
    version_no: Mapped[int]
    text: Mapped[str]
    edited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    edited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
