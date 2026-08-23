"""unique invoice gateway reference

Revision ID: f6a7b8c9d0e1
Revises: e4f5a6b7c8d9
Create Date: 2026-08-23
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_invoices_gateway_reference", "invoices", ["gateway_reference"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_invoices_gateway_reference", "invoices", type_="unique"
    )
