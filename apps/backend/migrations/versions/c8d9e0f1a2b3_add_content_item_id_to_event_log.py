"""add content_item_id to event_log

Revision ID: c8d9e0f1a2b3
Revises: b3e4f5a6b7c8
Create Date: 2026-08-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("event_log", sa.Column("content_item_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_event_log_content_item_id"), "event_log", ["content_item_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_event_log_content_item_id"), table_name="event_log")
    op.drop_column("event_log", "content_item_id")
