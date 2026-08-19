"""add DOANH_NGHIEP to plan enum on workspaces and invoices

Revision ID: e8f49b1a2c3d
Revises: b9d9c3205605
Create Date: 2026-08-19 16:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f49b1a2c3d'
down_revision: Union[str, Sequence[str], None] = 'b9d9c3205605'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'workspaces',
        'plan',
        existing_type=sa.Enum('TRIAL', 'TIEM_NHO', 'TOAN_DIEN', name='plan', native_enum=False),
        type_=sa.Enum('TRIAL', 'TIEM_NHO', 'TOAN_DIEN', 'DOANH_NGHIEP', name='plan', native_enum=False),
        existing_nullable=False,
    )
    op.alter_column(
        'invoices',
        'plan',
        existing_type=sa.Enum('TRIAL', 'TIEM_NHO', 'TOAN_DIEN', name='plan', native_enum=False),
        type_=sa.Enum('TRIAL', 'TIEM_NHO', 'TOAN_DIEN', 'DOANH_NGHIEP', name='plan', native_enum=False),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'invoices',
        'plan',
        existing_type=sa.Enum('TRIAL', 'TIEM_NHO', 'TOAN_DIEN', 'DOANH_NGHIEP', name='plan', native_enum=False),
        type_=sa.Enum('TRIAL', 'TIEM_NHO', 'TOAN_DIEN', name='plan', native_enum=False),
        existing_nullable=False,
    )
    op.alter_column(
        'workspaces',
        'plan',
        existing_type=sa.Enum('TRIAL', 'TIEM_NHO', 'TOAN_DIEN', 'DOANH_NGHIEP', name='plan', native_enum=False),
        type_=sa.Enum('TRIAL', 'TIEM_NHO', 'TOAN_DIEN', name='plan', native_enum=False),
        existing_nullable=False,
    )
