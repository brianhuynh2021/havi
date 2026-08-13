"""leads.content_item_id column and foreign key

Revision ID: c9f87d6e5a43
Revises: b8e52d1f4a90
Create Date: 2026-08-13 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9f87d6e5a43"
down_revision: Union[str, None] = "b8e52d1f4a90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("content_item_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_leads_content_item_id"), "leads", ["content_item_id"], unique=False
    )
    op.create_foreign_key(
        "fk_leads_content_item_id_content_items",
        "leads",
        "content_items",
        ["content_item_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_leads_content_item_id_content_items", "leads", type_="foreignkey"
    )
    op.drop_index(op.f("ix_leads_content_item_id"), table_name="leads")
    op.drop_column("leads", "content_item_id")
