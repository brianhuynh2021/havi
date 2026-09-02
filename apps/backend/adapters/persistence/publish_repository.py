from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import Channel, PublishFailureKind, PublishStatus
from domain.models.publish import PublishJob

#: Số lần thử tối đa cho lỗi tạm thời. Quá số này thì sang dead-letter và chờ
#: người bấm thử lại — một bài hỏng không được đập API nền tảng mãi.
MAX_ATTEMPTS = 4

#: Backoff giữa các lần thử. Tăng dần để rate limit có thời gian giãn ra.
BACKOFF_SECONDS = [60, 300, 900]


def build_idempotency_key(
    *, content_item_id: UUID, channel: Channel, scheduled_at: datetime
) -> str:
    """Khoá chống đăng trùng.

    Gồm cả `scheduled_at` để đổi lịch ra job mới — đó là ý muốn, vì đổi giờ
    đăng là một lần đăng khác. Chuẩn hoá về UTC trước khi format: cùng một mốc
    thời gian viết ở hai offset khác nhau phải ra cùng một khoá, nếu không thì
    reschedule sang đúng giờ cũ lại sinh key mới và đăng trùng.
    """
    utc = scheduled_at.astimezone(UTC) if scheduled_at.tzinfo else scheduled_at
    return f"{content_item_id}:{channel.value}:{utc.strftime('%Y%m%dT%H%M%S')}"


class PublishRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, job_id: UUID) -> PublishJob | None:
        result = await self._session.execute(
            select(PublishJob).where(PublishJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> PublishJob | None:
        result = await self._session.execute(
            select(PublishJob).where(PublishJob.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def enqueue(
        self,
        *,
        workspace_id: UUID,
        content_item_id: UUID,
        channel: Channel,
        scheduled_at: datetime,
    ) -> tuple[PublishJob, bool]:
        """Tạo job, trả `(job, created)`.

        Bắt `IntegrityError` thay vì chỉ kiểm tra trước khi insert: hai worker
        cùng quét một bài đến hạn đều thấy "chưa có job" rồi cùng insert. Unique
        constraint là thứ duy nhất thật sự chặn được vì Postgres cưỡng chế nó,
        không phụ thuộc thứ tự chạy của code.
        """
        key = build_idempotency_key(
            content_item_id=content_item_id, channel=channel, scheduled_at=scheduled_at
        )
        existing = await self.get_by_idempotency_key(key)
        if existing is not None:
            return existing, False

        job = PublishJob(
            workspace_id=workspace_id,
            content_item_id=content_item_id,
            channel=channel,
            idempotency_key=key,
            scheduled_at=scheduled_at,
            status=PublishStatus.PENDING,
        )
        self._session.add(job)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            duplicate = await self.get_by_idempotency_key(key)
            if duplicate is None:
                raise
            return duplicate, False
        return job, True

    async def claim_due(self, *, now: datetime, limit: int = 20) -> list[PublishJob]:
        """Lấy các job đến hạn và KHOÁ chúng cho worker này.

        `FOR UPDATE SKIP LOCKED` là mấu chốt: hai worker chạy song song, worker
        thứ hai bỏ qua hàng đang bị khoá thay vì đợi hoặc lấy trùng.

        Truy vấn sử dụng index ix_publish_jobs_status_due để tìm các job pending
        đến hạn nhanh nhất.
        """
        result = await self._session.execute(
            select(PublishJob)
            .where(
                PublishJob.status == PublishStatus.PENDING,
                PublishJob.scheduled_at <= now,
                (PublishJob.next_attempt_at.is_(None)) | (PublishJob.next_attempt_at <= now),
            )
            .order_by(PublishJob.scheduled_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        jobs = list(result.scalars().all())
        for job in jobs:
            job.status = PublishStatus.IN_FLIGHT
            job.attempt_count += 1
        await self._session.flush()
        return jobs

    async def claim_one(self, *, job_id: UUID, workspace_id: UUID) -> PublishJob | None:
        """Khoá đúng một job đang `pending` — dùng cho lượt thử lại thủ công.

        Cùng `SKIP LOCKED` như `claim_due` và cùng lý do: nếu scheduler vừa nhận
        job này thì trả `None` để người bấm "thử lại" không chạy song song với
        worker và đăng hai lần. `workspace_id` nằm trong điều kiện WHERE chứ
        không kiểm sau khi đọc — tenant scope phải ở tầng query.

        Trả `None` cũng khi job không còn `pending` (đã chạy xong, hoặc vẫn ở
        `dead_letter` vì chưa ai reset) — không ai được nhảy qua bước reset.
        """
        result = await self._session.execute(
            select(PublishJob)
            .where(
                PublishJob.id == job_id,
                PublishJob.workspace_id == workspace_id,
                PublishJob.status == PublishStatus.PENDING,
            )
            .with_for_update(skip_locked=True)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return None
        job.status = PublishStatus.IN_FLIGHT
        job.attempt_count += 1
        await self._session.flush()
        return job

    async def get(self, *, job_id: UUID, workspace_id: UUID) -> PublishJob | None:
        result = await self._session.execute(
            select(PublishJob).where(
                PublishJob.id == job_id, PublishJob.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def mark_succeeded(
        self, job: PublishJob, *, external_post_id: str, published_at: datetime
    ) -> PublishJob:
        job.status = PublishStatus.SUCCEEDED
        job.external_post_id = external_post_id
        job.published_at = published_at
        job.failure_kind = None
        job.failure_detail = None
        await self._session.flush()
        return job

    async def mark_failed(
        self, job: PublishJob, *, kind: PublishFailureKind, detail: str
    ) -> PublishJob:
        """Ghi lỗi và quyết định còn thử lại nữa hay không.

        Chỉ `TEMPORARY` mới được retry. `AUTH_PERMISSION` retry cũng vẫn hỏng
        cho tới khi chủ tiệm nối lại kênh, còn `VALIDATION_PERMANENT` thì cùng
        payload sẽ bị từ chối y hệt — cả hai đi thẳng dead-letter để không đập
        vào API nền tảng vô ích.
        """
        job.failure_kind = kind
        job.failure_detail = detail[:1000]

        retryable = kind is PublishFailureKind.TEMPORARY
        if retryable and job.attempt_count < MAX_ATTEMPTS:
            delay = BACKOFF_SECONDS[min(job.attempt_count - 1, len(BACKOFF_SECONDS) - 1)]
            job.status = PublishStatus.PENDING
            job.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay)
        else:
            job.status = PublishStatus.DEAD_LETTER
            job.next_attempt_at = None

        await self._session.flush()
        return job

    async def mark_pending_reconciliation(self, job: PublishJob, *, detail: str) -> PublishJob:
        """Dừng retry khi kết quả bên ngoài không xác định.

        Cùng job không được quay lại `pending` trước khi có bằng chứng bài chưa
        được tạo; unique key trong DB không bảo vệ khỏi việc retry chính job đó.
        """
        job.status = PublishStatus.PENDING_RECONCILIATION
        job.failure_kind = PublishFailureKind.AMBIGUOUS_OUTCOME
        job.failure_detail = detail[:1000]
        job.next_attempt_at = None
        await self._session.flush()
        return job

    async def list_for_workspace(
        self, *, workspace_id: UUID, status: PublishStatus | None = None
    ) -> list[PublishJob]:
        filters = [PublishJob.workspace_id == workspace_id]
        if status is not None:
            filters.append(PublishJob.status == status)
        result = await self._session.execute(
            select(PublishJob).where(*filters).order_by(PublishJob.scheduled_at.desc())
        )
        return list(result.scalars().all())

    async def status_counts_for_window(
        self, *, workspace_id: UUID, start: datetime, end: datetime
    ) -> dict[PublishStatus, int]:
        """Đếm publish job đã được xử lý/cập nhật trong một cửa sổ vận hành."""
        result = await self._session.execute(
            select(PublishJob.status, func.count())
            .where(
                PublishJob.workspace_id == workspace_id,
                PublishJob.updated_at >= start,
                PublishJob.updated_at < end,
            )
            .group_by(PublishJob.status)
        )
        return {status: count for status, count in result.all()}

    async def reset_for_manual_retry(self, job: PublishJob) -> PublishJob:
        """Người bấm "thử lại" trên một job dead-letter.

        Đặt lại `attempt_count` về 0: đây là quyết định của con người sau khi đã
        sửa nguyên nhân (nối lại kênh, sửa nội dung), nên cho nó đủ lượt thử như
        job mới thay vì kế thừa số lần hỏng cũ.
        """
        job.status = PublishStatus.PENDING
        job.attempt_count = 0
        job.next_attempt_at = None
        job.failure_kind = None
        job.failure_detail = None
        await self._session.flush()
        return job

    async def cancel_pending_for_item(
        self, *, content_item_id: UUID, reason: str = "Bản nháp bị chỉnh sửa sau khi duyệt"
    ) -> list[PublishJob]:
        """Huỷ các publish job đang pending của một content item khi nội dung bị chỉnh sửa sau duyệt."""
        result = await self._session.execute(
            select(PublishJob).where(
                PublishJob.content_item_id == content_item_id,
                PublishJob.status == PublishStatus.PENDING,
            )
        )
        jobs = list(result.scalars().all())
        for job in jobs:
            job.status = PublishStatus.DEAD_LETTER
            job.failure_kind = PublishFailureKind.VALIDATION_PERMANENT
            job.failure_detail = reason[:1000]
            job.next_attempt_at = None
        await self._session.flush()
        return jobs

    async def list_pending_reconciliation(
        self, *, older_than: datetime | None = None
    ) -> list[PublishJob]:
        """Danh sách publish job đang chờ đối soát kết quả."""
        filters = [PublishJob.status == PublishStatus.PENDING_RECONCILIATION]
        if older_than is not None:
            filters.append(PublishJob.updated_at <= older_than)
        result = await self._session.execute(
            select(PublishJob).where(*filters).order_by(PublishJob.updated_at.asc())
        )
        return list(result.scalars().all())

