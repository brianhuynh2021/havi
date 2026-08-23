"""Widen publish status for pending reconciliation.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "publish_jobs",
        "status",
        existing_type=sa.String(length=11),
        type_=sa.String(length=22),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "publish_jobs",
        "status",
        existing_type=sa.String(length=22),
        type_=sa.String(length=11),
        existing_nullable=False,
    )
