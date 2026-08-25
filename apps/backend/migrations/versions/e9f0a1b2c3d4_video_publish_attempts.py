"""video_publish_attempts — chặn đăng trùng ở tầng Postgres

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-08-25

Partial unique index là điểm chính của migration này. Một `if` trong service
thua ngay khi hai worker cùng nhận job hoặc chủ tiệm bấm nút hai lần trong một
giây; ràng buộc của Postgres thì không thua.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "e9f0a1b2c3d4"
down_revision: str | None = "d8e9f0a1b2c3"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "video_publish_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column(
            "video_render_job_id",
            sa.Uuid(),
            sa.ForeignKey("video_render_jobs.id"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("external_post_id", sa.String(), nullable=True),
        sa.Column("permalink_url", sa.String(), nullable=True),
        sa.Column("failure_kind", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("reconcile_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settled_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_video_publish_attempts_idem"),
    )
    op.create_index(
        "ix_video_publish_attempts_workspace",
        "video_publish_attempts",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_video_publish_attempts_video_render_job_id",
        "video_publish_attempts",
        ["video_render_job_id"],
    )
    # Một job chỉ có đúng một lần gửi còn sống. Lần `failed` không tính, nên thử
    # lại sau khi hỏng vẫn được — chỉ "đang gửi" và "đã đăng" mới khoá.
    #
    # CHỮ HOA là bắt buộc: `Enum(..., native_enum=False)` của SQLAlchemy lưu
    # **tên** thành viên enum (`PENDING`), không phải giá trị (`pending`). Viết
    # chữ thường ở đây thì index không bao giờ khớp hàng nào — ràng buộc vẫn tồn
    # tại, chỉ là không chặn gì cả. Test
    # `test_rang_buoc_postgres_chan_lan_gui_thu_hai_khi_lan_dau_con_pending`
    # tồn tại để bắt đúng lỗi này.
    op.create_index(
        "uq_video_publish_attempts_live",
        "video_publish_attempts",
        ["video_render_job_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'PUBLISHED')"),
    )


def downgrade() -> None:
    op.drop_index("uq_video_publish_attempts_live", table_name="video_publish_attempts")
    op.drop_index(
        "ix_video_publish_attempts_video_render_job_id", table_name="video_publish_attempts"
    )
    op.drop_index("ix_video_publish_attempts_workspace", table_name="video_publish_attempts")
    op.drop_table("video_publish_attempts")
