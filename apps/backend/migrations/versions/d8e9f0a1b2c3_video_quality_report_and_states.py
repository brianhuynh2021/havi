"""video_render_jobs: quality_report, contact_sheet, và nới cột status

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-08-25

`status` dùng `Enum(native_enum=False)` nên ở Postgres nó là VARCHAR có độ dài
đúng bằng giá trị dài nhất của enum lúc tạo bảng — `varchar(9)` cho "cancelled".
Thêm `pending_reconciliation` (22 ký tự) mà quên nới cột thì INSERT lỗi
`StringDataRightTruncation` ngay lúc chạy, không phải lúc migrate.

SQLAlchemy 2.0 mặc định `create_constraint=False` nên không có CHECK nào để dựng
lại. Chỗ chặn giá trị lạ là `domain/policies/video_job_state.py`, và nó chặn
được nhiều hơn một CHECK — CHECK chỉ biết giá trị nào tồn tại, không biết cú
nhảy nào hợp lệ.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d8e9f0a1b2c3"
down_revision: str | None = "c7d8e9f0a1b2"
branch_labels: str | None = None
depends_on: str | None = None


#: Độ dài giá trị dài nhất của `VideoRenderStatus` — "pending_reconciliation".
_STATUS_LEN = 22
_OLD_STATUS_LEN = 9


def upgrade() -> None:
    op.alter_column(
        "video_render_jobs",
        "status",
        type_=sa.String(length=_STATUS_LEN),
        existing_type=sa.String(length=_OLD_STATUS_LEN),
        existing_nullable=False,
    )
    op.add_column(
        "video_render_jobs",
        sa.Column("quality_report", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "video_render_jobs",
        sa.Column("contact_sheet_object_key", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("video_render_jobs", "contact_sheet_object_key")
    op.drop_column("video_render_jobs", "quality_report")
    # Trạng thái mới không tồn tại ở schema cũ — quy về `failed` trước khi thu cột,
    # nếu không ALTER sẽ lỗi trên chính những hàng đang dùng giá trị dài.
    op.execute(
        "UPDATE video_render_jobs SET status = 'FAILED' WHERE length(status) > "
        f"{_OLD_STATUS_LEN}"
    )
    op.alter_column(
        "video_render_jobs",
        "status",
        type_=sa.String(length=_OLD_STATUS_LEN),
        existing_type=sa.String(length=_STATUS_LEN),
        existing_nullable=False,
    )
