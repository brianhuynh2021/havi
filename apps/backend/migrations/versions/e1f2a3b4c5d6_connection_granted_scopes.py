"""platform_connections.granted_scopes

Lưu quyền nền tảng thực sự cấp cho từng kết nối, để Havi bật/tắt tính năng theo
đúng những gì kết nối đó làm được thay vì đòi đủ quyền mới cho nối.

NULL = kết nối cũ, nối từ trước khi có cột này. Khác hẳn `{}` (đã hỏi và biết
chắc là không có quyền nào): chỗ đọc phải coi NULL là "không rõ" và cho phép
thử, nếu không mọi kết nối đang chạy sẽ bị tắt hết tính năng sau khi deploy.

Revision ID: e1f2a3b4c5d6
Revises: d9e0f1a2b3c4
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e1f2a3b4c5d6"
down_revision = "d9e0f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "platform_connections",
        sa.Column(
            "granted_scopes",
            postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("platform_connections", "granted_scopes")
