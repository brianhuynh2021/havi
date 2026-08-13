"""inbox_items.external_message_id + unique constraint chống webhook trùng

Nền tảng gửi lại cùng một sự kiện khi không nhận được 200 kịp. Ràng buộc unique
ở Postgres là chỗ duy nhất chặn được chắc chắn: kiểm tra bằng SELECT trước INSERT
thì hai worker chạy song song đều thấy rỗng và cùng ghi.

`external_message_id` cho phép NULL để item tạo tay / seed local không bị chặn —
Postgres coi mỗi NULL là khác nhau trong unique index.

Revision ID: a3d41c9b2e77
Revises: f9208a17bc34
Create Date: 2026-08-13 14:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3d41c9b2e77"
down_revision: Union[str, None] = "f9208a17bc34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inbox_items",
        sa.Column("external_message_id", sa.String(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_inbox_items_external_message",
        "inbox_items",
        ["workspace_id", "platform", "external_message_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_inbox_items_external_message", "inbox_items", type_="unique"
    )
    op.drop_column("inbox_items", "external_message_id")
