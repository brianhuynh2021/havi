"""performance composite indexes for content, publish jobs, and inbox

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-09-02
"""

from alembic import op

revision = "c5d6e7f8a9b0"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_content_items_ws_status_sched",
        "content_items",
        ["workspace_id", "status", "scheduled_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_publish_jobs_status_due",
        "publish_jobs",
        ["status", "next_attempt_at", "scheduled_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_inbox_items_ws_status_created",
        "inbox_items",
        ["workspace_id", "status", "created_at"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_inbox_items_ws_status_created", table_name="inbox_items", if_exists=True)
    op.drop_index("ix_publish_jobs_status_due", table_name="publish_jobs", if_exists=True)
    op.drop_index("ix_content_items_ws_status_sched", table_name="content_items", if_exists=True)
