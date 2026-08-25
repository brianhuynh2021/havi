"""video_posts thay video_render_jobs — Havi không dựng video nữa

Havi chuyển sang **chỉ nhận clip có sẵn rồi đăng**: chủ tiệm tự quay và tự cắt
bằng công cụ họ đã quen, Havi lo phần đăng đúng giờ và đối soát với Facebook.

Nên toàn bộ cột phục vụ việc dựng bị bỏ: kịch bản dựng (`edit_plan`), tiến độ
render, engine, file đầu ra, kết quả chấm chất lượng, ảnh lưới khung hình, cờ
demo. Thay vào đó là hai cột mô tả *bài đăng*: `caption` (nội dung thật sẽ lên
Trang) và `channel` (kênh đích, hiện chỉ Reels).

Đổi tên bảng chứ không tạo bảng mới: các bản ghi đang có vẫn là những video thật
đã đăng hoặc đang chờ, và mã bài Facebook trong `video_publish_attempts` trỏ về
chúng. Mất liên kết đó nghĩa là mất khả năng đối soát — đúng thứ mà cả tầng này
sinh ra để giữ.

Revision ID: a1b2c3d4e5f6
Revises: e9f0a1b2c3d4
"""

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "e9f0a1b2c3d4"
branch_labels = None
depends_on = None

#: Trạng thái cũ đã biến mất cùng bước dựng. `title` cũ trở thành `caption`.
_DROPPED_COLUMNS = (
    "edit_plan",
    "progress_percent",
    "renderer_engine",
    "output_media_id",
    "output_url",
    "quality_report",
    "contact_sheet_object_key",
    "is_demo",
    "target_aspect_ratio",
    "started_at",
)


def upgrade() -> None:
    op.rename_table("video_render_jobs", "video_posts")

    # Index mang tên bảng cũ — đổi luôn để tên không nói dối về nơi nó sống.
    op.execute("ALTER INDEX ix_video_render_jobs_workspace_status "
               "RENAME TO ix_video_posts_workspace_status")
    op.execute("ALTER INDEX ix_video_render_jobs_created_at "
               "RENAME TO ix_video_posts_created_at")

    op.alter_column("video_posts", "title", new_column_name="caption")
    op.alter_column("video_posts", "completed_at", new_column_name="published_at")

    op.add_column(
        "video_posts",
        sa.Column("channel", sa.String(), nullable=False, server_default="REELS"),
    )
    op.add_column(
        "video_posts",
        sa.Column("source_object_key", sa.String(), nullable=False, server_default=""),
    )

    for column in _DROPPED_COLUMNS:
        op.drop_column("video_posts", column)

    # Bản ghi cũ đang ở một trạng thái thuộc bước dựng không còn tồn tại. Đưa về
    # `FAILED_PERMANENT` chứ không phải `READY_FOR_REVIEW`: chúng chưa từng có
    # clip nguồn hợp lệ theo mô hình mới, và cho chúng trông như sẵn sàng đăng là
    # cách nhanh nhất để một file rác lên Trang khách.
    op.execute(
        "UPDATE video_posts SET status = 'FAILED_PERMANENT' "
        "WHERE status IN ('QUEUED', 'RENDERING', 'QUALITY_CHECKING', 'COMPLETED')"
    )

    op.alter_column("video_publish_attempts", "video_render_job_id",
                    new_column_name="video_post_id")


def downgrade() -> None:
    op.alter_column("video_publish_attempts", "video_post_id",
                    new_column_name="video_render_job_id")

    op.drop_column("video_posts", "source_object_key")
    op.drop_column("video_posts", "channel")

    op.add_column("video_posts", sa.Column("edit_plan", sa.JSON(), nullable=True))
    op.add_column("video_posts", sa.Column("progress_percent", sa.Integer(), server_default="0"))
    op.add_column("video_posts", sa.Column("renderer_engine", sa.String(), server_default="FFMPEG"))
    op.add_column("video_posts", sa.Column("output_media_id", sa.UUID(), nullable=True))
    op.add_column("video_posts", sa.Column("output_url", sa.String(), nullable=True))
    op.add_column("video_posts", sa.Column("quality_report", sa.JSON(), nullable=True))
    op.add_column("video_posts", sa.Column("contact_sheet_object_key", sa.String(), nullable=True))
    op.add_column("video_posts", sa.Column("is_demo", sa.Boolean(), server_default="false"))
    op.add_column("video_posts", sa.Column("target_aspect_ratio", sa.String(), server_default="9:16"))
    op.add_column("video_posts", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))

    op.alter_column("video_posts", "published_at", new_column_name="completed_at")
    op.alter_column("video_posts", "caption", new_column_name="title")

    op.execute("ALTER INDEX ix_video_posts_workspace_status "
               "RENAME TO ix_video_render_jobs_workspace_status")
    op.execute("ALTER INDEX ix_video_posts_created_at "
               "RENAME TO ix_video_render_jobs_created_at")
    op.rename_table("video_posts", "video_render_jobs")
