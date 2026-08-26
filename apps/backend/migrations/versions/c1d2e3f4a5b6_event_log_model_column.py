"""event_log model column

Cột `provider` một mình không đủ để quy token ra tiền: trong cùng một nhà cung
cấp, hai model chênh nhau tới hơn mười lần đơn giá. Model thật do biến môi
trường quyết định (`HAVI_ANTHROPIC_MODEL`…), nên tính giá theo provider là lấy
giá của model mình *đoán* đang chạy.

`LLMResponse.model` đã có sẵn từ trước, chỉ là bị vứt đi trước khi tới event_log.

Nullable vì mọi dòng ghi trước migration này không có model để điền. Chỗ tính
tiền rơi về đơn giá đắt nhất của provider cho những dòng đó — xem
`domain/policies/pricing.py`.

Revision ID: c1d2e3f4a5b6
Revises: 8a71d3c42b90
Create Date: 2026-08-26 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = '8a71d3c42b90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('event_log', sa.Column('model', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('event_log', 'model')
