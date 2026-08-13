"""media_assets: thông số video đọc lúc upload

Cột NULL-able có chủ đích: NULL = "chưa/không đọc được", khác hẳn 0. Ảnh và audio
luôn để NULL. Xem `domain/policies/video_constraints.py`.

Revision ID: b8e52d1f4a90
Revises: a3d41c9b2e77
Create Date: 2026-08-13 15:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8e52d1f4a90"
down_revision: Union[str, None] = "a3d41c9b2e77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "media_assets", sa.Column("duration_seconds", sa.Float(), nullable=True)
    )
    op.add_column("media_assets", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("media_assets", sa.Column("height", sa.Integer(), nullable=True))
    op.add_column("media_assets", sa.Column("aspect_ratio", sa.String(), nullable=True))
    op.add_column("media_assets", sa.Column("has_audio", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("media_assets", "has_audio")
    op.drop_column("media_assets", "aspect_ratio")
    op.drop_column("media_assets", "height")
    op.drop_column("media_assets", "width")
    op.drop_column("media_assets", "duration_seconds")
