"""video_publish_attempts — mỗi lần Havi gửi một video sang nền tảng.

Vì sao cần bảng riêng thay vì vài cột trên `video_posts`: chặn đăng trùng
phải nằm ở Postgres, không nằm ở service. Một `if job.status != PUBLISHING` trong
Python thua ngay khi có hai worker cùng nhận job, hoặc khi chủ tiệm bấm nút hai
lần trong một giây. Ràng buộc unique thì không thua.

Hai ràng buộc, hai vai trò khác nhau:

* `uq_video_publish_attempts_idem` trên `idempotency_key` — cùng một ý định đăng
  chỉ tạo được một hàng, kể cả khi request bị gửi lại.
* `uq_video_publish_attempts_live` là **partial unique** trên `video_post_id`
  với điều kiện `status IN ('PENDING','PUBLISHED')` — một job chỉ có đúng một
  lần gửi còn sống. Lần `failed` thì không tính, nên thử lại sau khi hỏng vẫn được.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import Channel, PublishFailureKind, VideoPublishAttemptStatus
from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class VideoPublishAttempt(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "video_publish_attempts"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_video_publish_attempts_idem"),
        Index(
            "uq_video_publish_attempts_live",
            "video_post_id",
            unique=True,
            # Chữ hoa: SQLAlchemy lưu tên thành viên enum, không phải giá trị.
            postgresql_where="status IN ('PENDING', 'PUBLISHED')",
        ),
        Index("ix_video_publish_attempts_workspace", "workspace_id", "status"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    video_post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_posts.id"), index=True
    )
    channel: Mapped[Channel] = mapped_column(Enum(Channel, native_enum=False))
    idempotency_key: Mapped[str] = mapped_column()

    status: Mapped[VideoPublishAttemptStatus] = mapped_column(
        Enum(VideoPublishAttemptStatus, native_enum=False),
        default=VideoPublishAttemptStatus.PENDING,
    )

    #: ID video trên nền tảng. Không bao giờ được bịa: id bịa nghĩa là về sau
    #: không đối soát được, mà đối soát là thứ duy nhất chặn đăng trùng.
    external_post_id: Mapped[str | None] = mapped_column(default=None, nullable=True)
    permalink_url: Mapped[str | None] = mapped_column(default=None, nullable=True)

    failure_kind: Mapped[PublishFailureKind | None] = mapped_column(
        Enum(PublishFailureKind, native_enum=False), default=None, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(default=None, nullable=True)

    #: Số lần đã đối soát. Dùng để dừng hẳn thay vì kiểm mãi một video đã mất.
    reconcile_attempts: Mapped[int] = mapped_column(default=0)

    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
