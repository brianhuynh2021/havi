from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import Channel, ContentJobStatus, ContentStatus
from domain.models.content import ContentItem, ContentJob


class ContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- jobs ---------------------------------------------------------------

    async def get_job(self, *, workspace_id: UUID, job_id: UUID) -> ContentJob | None:
        result = await self._session.execute(
            select(ContentJob).where(
                ContentJob.id == job_id, ContentJob.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def get_job_by_idempotency_key(
        self, *, workspace_id: UUID, idempotency_key: str
    ) -> ContentJob | None:
        result = await self._session.execute(
            select(ContentJob).where(
                ContentJob.workspace_id == workspace_id,
                ContentJob.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def create_job(
        self, *, workspace_id: UUID, raw_inputs: list[dict], idempotency_key: str
    ) -> tuple[ContentJob, bool]:
        """Trả (job, created). `created=False` khi idempotency key đã tồn tại.

        Bắt IntegrityError thay vì chỉ check-trước-insert: hai request song song
        đều thấy "chưa có" rồi cùng insert, unique constraint là thứ duy nhất
        thật sự chặn được.
        """
        existing = await self.get_job_by_idempotency_key(
            workspace_id=workspace_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            return existing, False

        job = ContentJob(
            workspace_id=workspace_id,
            raw_inputs=raw_inputs,
            idempotency_key=idempotency_key,
        )
        self._session.add(job)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            duplicate = await self.get_job_by_idempotency_key(
                workspace_id=workspace_id, idempotency_key=idempotency_key
            )
            if duplicate is None:
                raise
            return duplicate, False
        return job, True

    async def mark_job_processing(self, job: ContentJob) -> ContentJob:
        job.status = ContentJobStatus.PROCESSING
        await self._session.flush()
        return job

    async def mark_job_drafts_ready(self, job: ContentJob) -> ContentJob:
        job.status = ContentJobStatus.DRAFTS_READY
        job.finished_at = datetime.now(UTC)
        await self._session.flush()
        return job

    async def mark_job_failed(self, job: ContentJob, *, reason: str) -> ContentJob:
        job.status = ContentJobStatus.FAILED
        job.failure_reason = reason[:500]
        job.finished_at = datetime.now(UTC)
        await self._session.flush()
        return job

    # --- items --------------------------------------------------------------

    async def create_item(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        channel: Channel,
        kind: str,
        text: str,
        media_note: str | None,
        status: ContentStatus,
    ) -> ContentItem:
        item = ContentItem(
            workspace_id=workspace_id,
            job_id=job_id,
            channel=channel,
            kind=kind,
            text=text,
            media_note=media_note,
            status=status,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def list_items_for_job(self, job_id: UUID) -> list[ContentItem]:
        result = await self._session.execute(
            select(ContentItem)
            .where(ContentItem.job_id == job_id)
            .order_by(ContentItem.created_at)
        )
        return list(result.scalars().all())

    async def get_item(self, *, workspace_id: UUID, item_id: UUID) -> ContentItem | None:
        result = await self._session.execute(
            select(ContentItem).where(
                ContentItem.id == item_id, ContentItem.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def list_items(
        self,
        *,
        workspace_id: UUID,
        status: ContentStatus | None = None,
        channel: Channel | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ContentItem], int]:
        filters = [ContentItem.workspace_id == workspace_id]
        if status is not None:
            filters.append(ContentItem.status == status)
        if channel is not None:
            filters.append(ContentItem.channel == channel)

        total = await self._session.execute(select(func.count()).where(*filters))
        rows = await self._session.execute(
            select(ContentItem)
            .where(*filters)
            .order_by(ContentItem.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total.scalar_one()
