"""Remove the retired CRM and sales-attribution tables.

Revision ID: 8a71d3c42b90
Revises: 4ec349283cb1
Create Date: 2026-08-25 20:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8a71d3c42b90"
down_revision: Union[str, Sequence[str], None] = "4ec349283cb1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("crm_nudges")
    op.drop_table("leads")


def downgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("reply_status", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("suggested_reply", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("revenue_vnd", sa.Integer(), server_default="0", nullable=False),
        sa.Column("order_id", sa.String(), nullable=True),
        sa.Column("content_item_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["content_item_id"], ["content_items.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_leads_workspace_id"), "leads", ["workspace_id"])
    op.create_index(op.f("ix_leads_content_item_id"), "leads", ["content_item_id"])

    op.create_table(
        "crm_nudges",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("nudge_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crm_nudges_lead_id"), "crm_nudges", ["lead_id"])
    op.create_index(op.f("ix_crm_nudges_status"), "crm_nudges", ["status"])
    op.create_index(op.f("ix_crm_nudges_workspace_id"), "crm_nudges", ["workspace_id"])
