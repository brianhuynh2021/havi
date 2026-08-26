"""chu kỳ thanh toán và phụ phí theo ghế / kênh

Hai vấn đề thương mại, một migration.

**Chu kỳ.** Thanh toán VietQR không có auto-renew: mỗi tháng khách phải chủ động
quyết định trả tiếp, và trong SaaS chuyển từ auto-renew sang thanh toán chủ động
làm churn tăng nhiều lần. Gói năm đổi mười hai quyết định thành một — đó là đối
sách mạnh nhất làm được mà không cần card-on-file.

**Phụ phí.** Trước đó bốn gói là bậc cố định: khách gói Khởi Nghiệp cần người thứ
tư phải nhảy lên Chuyên Nghiệp, 189.000đ → 369.000đ, gần gấp đôi cho một người.
Đó là bậc thang, không phải đòn bẩy doanh thu. Với phụ phí, người thứ tư là
+49.000đ, và net revenue retention tăng theo đúng mức khách lớn lên.

Lưu ở `workspaces` vì trần hiệu dụng phải đọc được ở mọi chỗ kiểm quyền, không
chỉ ở màn hoá đơn. Lưu **thêm** trên `invoices` vì hoá đơn là chứng từ: một dòng
chỉ ghi "238.000đ" thì sau này không dựng lại được nó gồm những gì.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-08-26 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, Sequence[str], None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    for table in ("workspaces", "invoices"):
        op.add_column(
            table,
            sa.Column(
                "billing_cycle",
                sa.String(),
                nullable=False,
                server_default="monthly",
            ),
        )
        op.add_column(
            table,
            sa.Column("extra_seats", sa.Integer(), nullable=False, server_default="0"),
        )
        op.add_column(
            table,
            sa.Column("extra_channels", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in ("invoices", "workspaces"):
        op.drop_column(table, "extra_channels")
        op.drop_column(table, "extra_seats")
        op.drop_column(table, "billing_cycle")
