"""event_log — bảng thật cho core.events.EventLogEntry.

Bảng **append-only**, cưỡng chế ở tầng database: migration f2a3b4c5d6e7 gắn
trigger chặn UPDATE/DELETE/TRUNCATE và tự tính hash chain. Đừng thêm code sửa
dòng ở đây — Postgres sẽ từ chối, và đó là chủ ý.
"""

import uuid

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class EventLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "event_log"
    __table_args__ = (
        Index("ix_event_log_workspace_created", "workspace_id", "created_at"),
        # Dùng bởi trigger hash chain để tìm dòng cuối của workspace trong
        # O(log n). Khai ở đây để `alembic check` không coi nó là drift —
        # migration f2a3b4c5d6e7 tạo index này.
        Index("ix_event_log_chain_tip", "workspace_id", "created_at", "id"),
    )

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(index=True, default=None)
    job_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(index=True, default=None)
    request_id: Mapped[str | None] = mapped_column(index=True, default=None)
    job_kind: Mapped[str]
    input_summary: Mapped[str] = mapped_column(default="")
    output_summary: Mapped[str] = mapped_column(default="")
    tokens_in: Mapped[int] = mapped_column(default=0)
    tokens_out: Mapped[int] = mapped_column(default=0)
    # Provider nào phục vụ lượt này. Cột riêng chứ không nhét trong
    # `output_summary`: cần lọc/GROUP BY được để trả lời "provider nào đang hỏng"
    # hay "bài này do model nào sinh", mà parse chuỗi tự do trong SQL thì mỗi câu
    # query một kiểu và sai âm thầm. Nullable cho dòng cũ ghi trước khi có cột này.
    #
    # Quota KHÔNG dùng cột này: Havi chặn theo *token*, không theo tiền, nên
    # không cần đơn giá của từng provider (xem `domain/policies/quota.py`).
    provider: Mapped[str | None] = mapped_column(default=None)
    # Model cụ thể — thứ thật sự quyết định đơn giá. Nullable cho dòng ghi
    # trước migration c1d2e3f4a5b6; những dòng đó rơi về giá đắt nhất của
    # provider ở `domain/policies/pricing.py`.
    model: Mapped[str | None] = mapped_column(default=None)
    duration_ms: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(default=None)

    # Hash chain — do trigger Postgres điền, KHÔNG phải Python. Xem migration
    # f2a3b4c5d6e7: tính ở tầng app thì một INSERT bằng psql sẽ tạo dòng không
    # hash và làm đứt chuỗi đúng ở chỗ cần kiểm.
    #
    # Nullable vì hai lý do khác nhau: dòng ghi trước migration này không có
    # hash, và `prev_hash` của dòng đầu mỗi workspace luôn NULL (không có gì
    # trước nó).
    row_hash: Mapped[str | None] = mapped_column(default=None)
    prev_hash: Mapped[str | None] = mapped_column(default=None)
