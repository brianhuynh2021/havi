"""content_items media_url column

Revision ID: f4a8b7c91234
Revises: 259c737f4350
Create Date: 2026-08-20 11:39:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a8b7c91234'
down_revision: Union[str, Sequence[str], None] = ('259c737f4350', 'e8f49b1a2c3d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('content_items', sa.Column('media_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('content_items', 'media_url')
