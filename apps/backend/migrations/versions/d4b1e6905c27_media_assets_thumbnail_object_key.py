"""media_assets.thumbnail_object_key column

Revision ID: d4b1e6905c27
Revises: c9f87d6e5a43
Create Date: 2026-08-13 19:30:00.000000

Nullable và không backfill: NULL nghĩa là "chưa trích được ảnh bìa", khác với
"clip không có khung nào". Asset video upload trước bản này sẽ ở NULL cho tới khi
được upload lại — không có job backfill vì bytes vẫn còn trên storage và một lượt
quét toàn bucket không đáng cho một ảnh xem trước.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4b1e6905c27"
down_revision: Union[str, None] = "c9f87d6e5a43"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "media_assets", sa.Column("thumbnail_object_key", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("media_assets", "thumbnail_object_key")
