"""outbox — Transactional Outbox cho việc đẩy job

Vá khe dual-write: trước đây `create_job()` ghi Postgres rồi `enqueue()` gọi
Redis ở hai bước riêng, nên process chết ở giữa để lại job `pending` mà không
worker nào biết. Xem docstring `domain/models/outbox.py`.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_outbox_topic", "outbox", ["topic"])
    op.create_index("ix_outbox_status", "outbox", ["status"])
    op.create_index("ix_outbox_available_at", "outbox", ["available_at"])
    op.create_index("ix_outbox_request_id", "outbox", ["request_id"])
    op.create_index("ix_outbox_workspace_id", "outbox", ["workspace_id"])

    # Index *một phần* — chỉ trên dòng `pending`, đúng câu hỏi duy nhất của
    # dispatcher. Index đầy đủ sẽ lớn theo toàn bộ lịch sử đã đẩy; bản một phần
    # chỉ lớn theo số việc đang tồn đọng, gần như luôn nhỏ.
    op.create_index(
        "ix_outbox_pending",
        "outbox",
        ["available_at", "created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_pending", table_name="outbox")
    op.drop_index("ix_outbox_workspace_id", table_name="outbox")
    op.drop_index("ix_outbox_request_id", table_name="outbox")
    op.drop_index("ix_outbox_available_at", table_name="outbox")
    op.drop_index("ix_outbox_status", table_name="outbox")
    op.drop_index("ix_outbox_topic", table_name="outbox")
    op.drop_table("outbox")
