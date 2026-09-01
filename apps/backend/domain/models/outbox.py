"""outbox — bảng trung gian giữa "đã ghi DB" và "đã đẩy vào hàng đợi".

Khe hở nó vá (dual-write problem). Trước đây `content_service` làm hai việc
không thể nguyên tử với nhau:

    job, created = await self._content.create_job(...)   # (1) ghi Postgres
    self._queue.enqueue_generate_drafts(...)             # (2) đẩy Redis

Process chết giữa (1) và (2) — hoặc Redis từ chối kết nối đúng lúc đó — thì job
nằm trong DB ở trạng thái `pending` **mãi mãi**, không worker nào biết nó tồn
tại. Người dùng thấy "Havi đang viết…" và chờ vô hạn. Ngược lại, đẩy Redis trước
rồi ghi DB thì worker có thể nhận job trước khi dòng tồn tại.

Cách vá: (2) trở thành một `INSERT` vào bảng này, **cùng transaction** với (1).
Hoặc cả hai cùng commit, hoặc cả hai cùng rollback — không còn trạng thái lửng
lơ. Một dispatcher chạy nền đọc outbox rồi mới gọi Redis.

Đánh đổi phải nói rõ: đây là **at-least-once**, không phải exactly-once.
Dispatcher có thể chết sau khi Celery nhận job nhưng trước khi kịp đánh dấu
`dispatched`, và job đó sẽ được đẩy lại. Havi chịu được vì mọi job đều có
`idempotency_key` với UNIQUE constraint ở DB (xem migration b7f77094b946) — lần
đẩy thứ hai không tạo thêm bài đăng nào. Exactly-once qua hai hệ thống là điều
không thể mà không có distributed transaction; at-least-once + idempotency là
cách giải quyết đúng, và nó chỉ đúng *vì* idempotency đã có sẵn.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import OutboxStatus
from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class OutboxEntry(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "outbox"
    __table_args__ = (
        # Index *một phần*, chỉ trên dòng chưa đẩy. Bảng này chủ yếu là lịch sử
        # đã xử lý, còn dispatcher luôn hỏi đúng một câu: "còn gì chưa đẩy?".
        # Index đầy đủ sẽ lớn theo toàn bộ lịch sử và ngày càng chậm; index một
        # phần thì chỉ lớn theo số việc đang tồn đọng — gần như luôn nhỏ.
        Index(
            "ix_outbox_pending",
            "available_at",
            "created_at",
            postgresql_where="status = 'pending'",
        ),
    )

    #: Tên task Celery, ví dụ `generate_drafts`. Lưu chuỗi chứ không enum: thêm
    #: task mới không nên cần migration, và outbox không phải chỗ cưỡng chế danh
    #: sách task — `dispatcher` đã có allow-list tường minh trong code.
    topic: Mapped[str] = mapped_column(String(64), index=True)
    #: Kwargs của task. JSONB chứ không JSON: cần query được `payload->>'job_id'`
    #: khi truy sự cố, mà JSON thuần phải parse lại mỗi lần đọc.
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[OutboxStatus] = mapped_column(
        String(16), default=OutboxStatus.PENDING, index=True
    )
    attempts: Mapped[int] = mapped_column(default=0)
    #: Backoff: dispatcher chỉ lấy dòng có `available_at <= now()`. Một upstream
    #: đang lỗi sẽ không bị hỏi lại 10 lần/giây.
    available_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, index=True
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    last_error: Mapped[str | None] = mapped_column(default=None)
    #: Truy vết ngược về HTTP request đã sinh ra việc này.
    request_id: Mapped[str | None] = mapped_column(default=None, index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(default=None, index=True)
