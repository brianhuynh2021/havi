"""Publish job — hàng đợi đăng bài lên nền tảng.

Đây là nơi cưỡng chế nguyên tắc #8 (ROADMAP §1): *publish job phải idempotent;
retry không được tạo bài đăng trùng*. Đăng trùng lên Fanpage của khách là lỗi
không sửa được — bài đã lên tường người ta rồi.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import Channel, PublishFailureKind, PublishStatus
from domain.models.base import Base, CreatedAtMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin


class PublishJob(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "publish_jobs"
    __table_args__ = (
        # Chốt chặn chống đăng trùng. Không dựa vào việc "kiểm tra trước khi
        # insert": hai worker cùng quét một bài đến hạn sẽ cùng thấy "chưa có
        # job" rồi cùng insert. Unique constraint là thứ duy nhất thật sự chặn
        # được, vì nó do Postgres cưỡng chế chứ không do thứ tự chạy của code.
        UniqueConstraint("idempotency_key", name="uq_publish_jobs_idempotency_key"),
        # Scheduler quét "job đến hạn còn chờ" mỗi phút — index theo đúng shape
        # của câu query đó.
        Index("ix_publish_jobs_status_scheduled", "status", "scheduled_at"),
        Index("ix_publish_jobs_status_due", "status", "next_attempt_at", "scheduled_at"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    content_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("content_items.id"), index=True)
    channel: Mapped[Channel] = mapped_column(Enum(Channel, native_enum=False))

    # Khoá idempotency dựng từ (content_item_id, channel, scheduled_at) — cùng
    # một bài, cùng kênh, cùng giờ đăng thì chỉ ra đúng một job dù scheduler
    # quét lại bao nhiêu lần. Đổi giờ đăng ra key mới, và đó là ý muốn: đổi lịch
    # là một lần đăng khác.
    idempotency_key: Mapped[str]

    status: Mapped[PublishStatus] = mapped_column(
        Enum(PublishStatus, native_enum=False), default=PublishStatus.PENDING
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    attempt_count: Mapped[int] = mapped_column(default=0)
    # Backoff: lần thử kế tiếp sớm nhất là lúc nào. Scheduler bỏ qua job chưa
    # tới hạn thử lại thay vì đập vào API nền tảng liên tục.
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # --- Kết quả -------------------------------------------------------------
    # ID bài trên nền tảng, có sau khi đăng thành công. Dùng để đối soát: nếu
    # job ở trạng thái mập mờ (worker chết giữa chừng) thì tra ID này để biết
    # bài đã lên hay chưa, thay vì đăng lại và tạo bài trùng.
    external_post_id: Mapped[str | None] = mapped_column(default=None)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    failure_kind: Mapped[PublishFailureKind | None] = mapped_column(
        Enum(PublishFailureKind, native_enum=False), default=None
    )
    # Chi tiết lỗi từng lần thử, để support tra được mà không cần đọc log server.
    failure_detail: Mapped[str | None] = mapped_column(default=None)
