"""video_render_jobs.is_demo — đánh dấu bản dựng mock, không cho đăng

Revision ID: c7d8e9f0a1b2
Revises: b1c2d3e4f5a6
Create Date: 2026-08-25

Cờ nằm ở DB chứ không suy ra từ config lúc đọc: một job dựng bằng mock renderer
hôm nay vẫn phải hiện là demo kể cả sau khi máy đã cài FFmpeg thật.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "video_render_jobs",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("video_render_jobs", "is_demo")
