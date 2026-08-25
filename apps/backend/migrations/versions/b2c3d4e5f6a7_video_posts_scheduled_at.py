"""video_posts.scheduled_at — video đi chung luồng hẹn giờ với bài viết

Chủ tiệm ngồi một buổi chuẩn bị nội dung cả tuần rồi rải lịch, thay vì phải mở
app đúng giờ mỗi ngày để bấm đăng. Bài viết đã làm được điều đó qua
`content_items.scheduled_at`; cột này cho video làm điều tương tự, để hai loại
nội dung không còn là hai luồng khác nhau trong đầu người dùng.

`NULL` = gửi ngay ở lượt worker kế tiếp, giữ nguyên hành vi cũ của các bản ghi
đã có.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_posts",
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Worker quét đúng một câu hỏi: "clip nào đã duyệt và tới giờ?". Index phủ
    # cả hai cột đó để lượt quét mỗi 5 phút không phải đọc cả bảng.
    op.create_index(
        "ix_video_posts_due",
        "video_posts",
        ["status", "scheduled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_video_posts_due", table_name="video_posts")
    op.drop_column("video_posts", "scheduled_at")
