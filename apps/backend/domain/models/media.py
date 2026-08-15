"""media_assets — xem docs/architecture/TECHNICAL_SPEC.md §3.

API chỉ lưu metadata; bytes nằm ở object storage (MinIO local, S3-compatible ở
production). `object_key` là nguồn sự thật để dựng URL — không lưu URL đầy đủ vì
domain/bucket có thể đổi khi chuyển provider.
"""

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import MediaStatus, MediaType
from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class MediaAsset(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (Index("ix_media_assets_workspace_status", "workspace_id", "status"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    object_key: Mapped[str] = mapped_column(unique=True)
    filename: Mapped[str]
    content_type: Mapped[str]
    type: Mapped[MediaType] = mapped_column(Enum(MediaType, native_enum=False))
    status: Mapped[MediaStatus] = mapped_column(
        Enum(MediaStatus, native_enum=False), default=MediaStatus.PENDING
    )
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    size_bytes: Mapped[int | None] = mapped_column(default=None)
    # Chỉ set khi client gọi /media/{id}/complete và API xác nhận object có thật.
    uploaded_at: Mapped[datetime | None] = mapped_column(default=None)

    # --- Thông số video, đọc bằng ffprobe lúc complete_upload ------------------
    #
    # NULL có nghĩa "chưa/không đọc được", không phải "bằng 0". Phân biệt được hai
    # thứ đó là điều kiện để `video_constraints` từ chối kiểm một video mù thay vì
    # tưởng nó hợp lệ. Asset ảnh/audio luôn để NULL.
    duration_seconds: Mapped[float | None] = mapped_column(default=None)
    width: Mapped[int | None] = mapped_column(default=None)
    height: Mapped[int | None] = mapped_column(default=None)
    aspect_ratio: Mapped[str | None] = mapped_column(default=None)
    has_audio: Mapped[bool | None] = mapped_column(default=None)

    # Ảnh bìa trích từ clip lúc complete_upload. Lưu object key chứ không lưu URL,
    # cùng lý do với `object_key`. NULL = chưa/không lấy được, và UI hiện
    # placeholder — không có ảnh bìa là chuyện nhỏ, không được chặn upload.
    thumbnail_object_key: Mapped[str | None] = mapped_column(default=None)
