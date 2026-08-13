"""inbox_items and leads tables

Revision ID: f9208a17bc34
Revises: 1f2a7c8d9e10
Create Date: 2026-08-13 03:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f9208a17bc34"
down_revision: Union[str, None] = "1f2a7c8d9e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inbox_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(), nullable=False),
        sa.Column("sentiment", sa.String(), nullable=True),
        sa.Column("ai_suggested_reply", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inbox_items_workspace_id"), "inbox_items", ["workspace_id"], unique=False)

    op.create_table(
        "leads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("reply_status", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("suggested_reply", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_leads_workspace_id"), "leads", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_leads_workspace_id"), table_name="leads")
    op.drop_table("leads")
    op.drop_index(op.f("ix_inbox_items_workspace_id"), table_name="inbox_items")
    op.drop_table("inbox_items")
