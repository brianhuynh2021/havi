"""event_log request_id

Revision ID: 1f2a7c8d9e10
Revises: 43eff08a8b58
Create Date: 2026-08-09 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1f2a7c8d9e10"
down_revision: Union[str, Sequence[str], None] = "43eff08a8b58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("event_log", sa.Column("request_id", sa.String(), nullable=True))
    op.create_index(op.f("ix_event_log_request_id"), "event_log", ["request_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_event_log_request_id"), table_name="event_log")
    op.drop_column("event_log", "request_id")
