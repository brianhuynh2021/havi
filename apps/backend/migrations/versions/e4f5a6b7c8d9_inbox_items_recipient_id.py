"""inbox items recipient_id column

Revision ID: e4f5a6b7c8d9
Revises: b9d9c3205605
Create Date: 2026-08-23 21:07:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = ('b9d9c3205605', 'f4a8b7c91234')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('inbox_items', sa.Column('recipient_id', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('inbox_items', 'recipient_id')
