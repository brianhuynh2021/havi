"""video_posts — một clip chủ tiệm tải lên, chờ duyệt rồi đăng.

Havi **không dựng và không biên tập video**. Chủ tiệm tự quay, tự cắt bằng công
cụ họ đã quen (CapCut, điện thoại), rồi tải lên đây. Việc của bảng này là giữ
đúng một thứ: *clip nào, caption nào, đã đi tới đâu trên đường lên Trang*.

Vì sao vẫn cần một bảng thay vì đăng thẳng lúc upload: giữa "chủ tiệm bấm đăng"
và "bài có thật trên Trang" có bốn bước đều có thể hỏng, và ba trong số đó hỏng
theo kiểu *mơ hồ* — đã gửi nhưng không biết Facebook nhận chưa. Không có hàng
lưu trạng thái thì cách duy nhất để biết là hỏi lại Facebook, và cách duy nhất
để hỏi là nhớ `video_id` — tức là vẫn cần bảng này.
"""

import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import Channel, VideoPostStatus
from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class VideoPost(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "video_posts"
    __table_args__ = (
        Index("ix_video_posts_workspace_status", "workspace_id", "status"),
        Index("ix_video_posts_created_at", "created_at"),
        # Worker quét "đã duyệt và tới giờ" mỗi 5 phút — index phủ đúng câu hỏi đó.
        Index("ix_video_posts_due", "status", "scheduled_at"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)

    #: Caption đăng kèm video. Đây là nội dung thật sẽ lên Trang, không phải tiêu
    #: đề nội bộ — nên nó được sửa được cho tới lúc duyệt.
    caption: Mapped[str] = mapped_column(default="")

    #: Kênh đích. Hiện chỉ `REELS`; cột tồn tại sẵn để thêm kênh không phải đổi
    #: schema, vì mỗi kênh có ràng buộc video riêng (xem `video_constraints`).
    channel: Mapped[Channel] = mapped_column(
        Enum(Channel, native_enum=False), default=Channel.REELS
    )

    status: Mapped[VideoPostStatus] = mapped_column(
        Enum(VideoPostStatus, native_enum=False), default=VideoPostStatus.READY_FOR_REVIEW
    )

    #: Clip gốc trong object storage. `nullable=False` về mặt ý nghĩa — một video
    #: post không có clip là vô nghĩa — nhưng để nullable vì FK tới media_assets
    #: có thể bị dọn trước khi bản ghi này bị dọn.
    source_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id"), default=None, nullable=True
    )

    #: Key của clip trong object storage, chốt ngay lúc tạo bản ghi.
    #: Lưu ở đây thay vì join sang `media_assets` mỗi lần đăng vì lúc gửi bytes
    #: sang Facebook cần đúng một thứ — file nào — và một cú join thêm ở đường
    #: nóng chỉ để lấy lại một chuỗi không đổi là chi phí không mua được gì.
    source_object_key: Mapped[str] = mapped_column(default="")

    #: Giờ Havi sẽ gửi clip đi, UTC. `None` = gửi ngay khi duyệt.
    #: Có cột này thì video đi chung một luồng với bài viết: chủ tiệm ngồi một
    #: buổi chuẩn bị cả tuần nội dung rồi rải lịch, thay vì phải mở app đúng giờ
    #: mỗi ngày để bấm đăng.
    scheduled_at: Mapped[datetime | None] = mapped_column(default=None, nullable=True)

    error_message: Mapped[str | None] = mapped_column(default=None, nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(default=None, nullable=True)
