"""Store Facebook app-scoped user ID for authenticated data deletion.

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a5b6c7d8e9f0"
down_revision: str | Sequence[str] | None = "f4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "platform_connections",
        sa.Column("external_user_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_platform_connections_external_user_id",
        "platform_connections",
        ["external_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_platform_connections_external_user_id",
        table_name="platform_connections",
    )
    op.drop_column("platform_connections", "external_user_id")
