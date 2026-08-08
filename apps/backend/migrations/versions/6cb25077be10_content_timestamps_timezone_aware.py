"""content timestamps timezone aware

Sản phẩm chạy ở Asia/Ho_Chi_Minh nhưng lưu UTC. Cột `TIMESTAMP WITHOUT TIME ZONE`
nuốt offset khi ghi datetime aware: bài hẹn 20h VN được lưu thành 20h rồi đọc lại
như 20h UTC — lệch 7 tiếng, và không phát hiện được sau khi đã ghi.

`USING ... AT TIME ZONE 'UTC'` là bắt buộc: mặc định Postgres diễn giải giá trị
naive theo `TimeZone` của session, mà dữ liệu cũ đã được ghi bằng giờ UTC.

Revision ID: 6cb25077be10
Revises: 32712ea2080b
Create Date: 2026-08-08 07:35:46.566038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6cb25077be10'
down_revision: Union[str, Sequence[str], None] = '32712ea2080b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = (
    ('content_item_versions', 'edited_at', False),
    ('content_items', 'scheduled_at', True),
    ('content_items', 'published_at', True),
    ('content_items', 'approved_at', True),
    ('content_jobs', 'finished_at', True),
)


def upgrade() -> None:
    """Upgrade schema."""
    for table, column, nullable in _COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=postgresql.TIMESTAMP(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table, column, nullable in reversed(_COLUMNS):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=postgresql.TIMESTAMP(),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
