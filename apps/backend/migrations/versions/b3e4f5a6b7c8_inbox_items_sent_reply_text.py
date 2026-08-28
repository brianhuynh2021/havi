"""Add sent_reply_text to inbox_items to preserve original ai_suggested_reply.

Revision ID: b3e4f5a6b7c8
Revises: a5b6c7d8e9f0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3e4f5a6b7c8"
down_revision: str | Sequence[str] | None = "a5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "inbox_items",
        sa.Column("sent_reply_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("inbox_items", "sent_reply_text")
