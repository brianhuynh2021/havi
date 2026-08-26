"""sửa server_default của billing_cycle: lưu TÊN enum, không lưu giá trị

Bug do migration `e3f4a5b6c7d8` gây ra.

`Enum(BillingCycle, native_enum=False)` của SQLAlchemy lưu **tên** thành viên
(`MONTHLY`), không lưu giá trị (`monthly`) — trừ khi truyền `values_callable`.
Toàn bộ enum khác trong Havi đã theo quy ước đó: cột `workspaces.plan` chứa
`TRIAL`, `TOAN_DIEN`, chứ không phải `trial`, `toan_dien`.

Migration trước đặt `server_default="monthly"`, tức là giá trị chữ thường. Hệ quả:

* mọi dòng đã tồn tại trước migration nhận `'monthly'`;
* đọc lại bất kỳ dòng nào trong số đó ném `LookupError: 'monthly' is not among
  the defined enum values`;
* lỗi đó xảy ra khi **hydrate ORM**, tức là bất cứ truy vấn nào load `Workspace`
  hay `Invoice` đều đổ — không chỉ màn Gói cước mà cả màn Cài đặt, đổi gói, và
  luồng thanh toán;
* dòng do ORM chèn *sau* migration lại đúng (`MONTHLY`), nên workspace mới hoạt
  động bình thường và bug chỉ hiện với dữ liệu cũ. Đó là lý do nó khó nhìn ra.

Chữa cả hai đầu: đổi dữ liệu sai về đúng tên, và đổi `server_default` để lần sau
Postgres điền đúng. Không sửa file migration cũ — lịch sử đã chạy thì để nguyên,
sửa bằng một bước tiến.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-08-26 18:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("workspaces", "invoices")


def upgrade() -> None:
    """Upgrade schema."""
    for table in _TABLES:
        # Dùng UPPER() thay vì so khớp từng giá trị: nếu sau này thêm thành viên
        # mới vào `BillingCycle`, dòng sai của nó cũng được chữa mà không phải sửa
        # migration này.
        op.execute(
            sa.text(
                f"UPDATE {table} SET billing_cycle = UPPER(billing_cycle) "
                "WHERE billing_cycle <> UPPER(billing_cycle)"
            )
        )
        op.alter_column(
            table,
            "billing_cycle",
            existing_type=sa.String(),
            existing_nullable=False,
            server_default="MONTHLY",
        )


def downgrade() -> None:
    """Downgrade schema.

    Trả về đúng trạng thái sai của `e3f4a5b6c7d8` — downgrade phải khôi phục
    nguyên trạng, kể cả khi nguyên trạng đó là một lỗi.
    """
    for table in _TABLES:
        op.alter_column(
            table,
            "billing_cycle",
            existing_type=sa.String(),
            existing_nullable=False,
            server_default="monthly",
        )
        op.execute(
            sa.text(f"UPDATE {table} SET billing_cycle = LOWER(billing_cycle)")
        )
