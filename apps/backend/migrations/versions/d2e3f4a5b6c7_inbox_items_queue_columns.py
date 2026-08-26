"""inbox_items: mốc phản hồi, người nhận việc, loại việc

Ba thứ hàng đợi việc cần mà bảng chưa có.

`replied_at` — bảng chỉ có `created_at`, không có `updated_at`, nên **thời gian
phản hồi khách không tính được**. Đó lại đúng là con số chứng minh giá trị sản
phẩm ("tuần trước bạn sót 12 tin hỏi giá"), và dữ liệu không ghi lúc nó xảy ra
thì sau này không dựng lại được. Đây là lý do migration này gấp hơn mọi tính năng.

`assigned_to_user_id` / `assigned_at` — resort có nhiều nhân viên trực ca. Không
có chỗ ghi "ai đang xử lý cái này" thì hai người cùng mở một tin và cùng trả lời
một khách. Cố ý **không** thêm trạng thái `in_progress` vào `InboxItemStatus`:
quyền sở hữu và vòng đời phản hồi là hai trục vuông góc nhau. Một việc có người
nhận vẫn đang ở `new`; gộp hai trục vào một enum là mất khả năng biểu diễn "có
người nhận nhưng chưa soạn xong".

`category` — sót "mấy giờ mở cửa" và sót "cho em xin báo giá" tốn tiền khác nhau
hoàn toàn, nên hàng đợi không được xếp thuần theo thời gian. Là chuỗi tự do chứ
không phải enum: bộ phân loại còn sẽ được sửa nhiều, và một enum trong Postgres
đổi giá trị thì cần thêm migration mỗi lần.

Index `(workspace_id, status)` cho truy vấn hàng đợi — màn làm việc chính đọc nó
mỗi lần mở, nên nó là truy vấn nóng nhất của sản phẩm.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-08-26 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "inbox_items", sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "inbox_items",
        sa.Column("assigned_to_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "inbox_items", sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("inbox_items", sa.Column("category", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_inbox_items_assigned_to_user",
        "inbox_items",
        "users",
        ["assigned_to_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_inbox_items_workspace_status", "inbox_items", ["workspace_id", "status"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_inbox_items_workspace_status", table_name="inbox_items")
    op.drop_constraint("fk_inbox_items_assigned_to_user", "inbox_items", type_="foreignkey")
    op.drop_column("inbox_items", "category")
    op.drop_column("inbox_items", "assigned_at")
    op.drop_column("inbox_items", "assigned_to_user_id")
    op.drop_column("inbox_items", "replied_at")
