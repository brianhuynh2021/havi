from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import Channel, ContentJobStatus, ContentStatus
from domain.models.content import ContentItem, ContentItemVersion, ContentJob


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
            if existing.status == ContentJobStatus.FAILED:
                existing.status = ContentJobStatus.QUEUED
                existing.failure_reason = None
                await self._session.flush()
                return existing, True
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
        # Commit ngay, không chỉ flush: nơi gọi đánh dấu `failed` rồi ném
        # `GenerationFailed` ngay sau đó, mà `session_scope` của worker rollback
        # khi gặp exception — flush suông sẽ bị cuốn theo và job kẹt ở `queued`
        # vĩnh viễn, frontend poll 3 phút rồi báo sai. Trạng thái thất bại là
        # thứ phải sống sót đúng cái exception đang đẩy nó đi.
        await self._session.commit()
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
            select(ContentItem).where(ContentItem.job_id == job_id).order_by(ContentItem.created_at)
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

    async def count_items_by_status(self, *, workspace_id: UUID) -> dict[ContentStatus, int]:
        """Đếm content item theo trạng thái trong đúng workspace.

        Dashboard P0 chỉ được hiện dữ liệu thật đã có. Không tự cộng fixture hay
        số từ domain chưa persist như leads/inbox, vì workspace mới phải thấy
        rỗng thay vì một tiệm mẫu.
        """
        rows = await self._session.execute(
            select(ContentItem.status, func.count())
            .where(ContentItem.workspace_id == workspace_id)
            .group_by(ContentItem.status)
        )
        return {status: count for status, count in rows.all()}

    async def count_published_by_channel(
        self, *, workspace_id: UUID, start: datetime, end: datetime
    ) -> dict[Channel, int]:
        rows = await self._session.execute(
            select(ContentItem.channel, func.count())
            .where(
                ContentItem.workspace_id == workspace_id,
                ContentItem.status == ContentStatus.PUBLISHED,
                ContentItem.published_at.is_not(None),
                ContentItem.published_at >= start,
                ContentItem.published_at < end,
            )
            .group_by(ContentItem.channel)
        )
        return {channel: count for channel, count in rows.all()}

    async def count_published_posts(
        self, *, workspace_id: UUID, start: datetime, end: datetime
    ) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                ContentItem.workspace_id == workspace_id,
                ContentItem.status == ContentStatus.PUBLISHED,
                ContentItem.published_at.is_not(None),
                ContentItem.published_at >= start,
                ContentItem.published_at < end,
            )
        )
        return result.scalar_one()

    async def get_item_for_update(self, *, workspace_id: UUID, item_id: UUID) -> ContentItem | None:
        """Như `get_item` nhưng khoá hàng (`SELECT ... FOR UPDATE`).

        Duyệt lẻ và "Duyệt & đăng hết" có thể chạy song song trên cùng một item
        (user bấm hai lần, hai tab). Không có row lock thì cả hai cùng đọc
        `pending_approval`, cùng thấy transition hợp lệ và cùng ghi `approved_by`
        — người duyệt cuối ghi đè người trước. Lock giữ cho lần thứ hai phải đọc
        lại trạng thái đã đổi và trả 409.
        """
        result = await self._session.execute(
            select(ContentItem)
            .where(ContentItem.id == item_id, ContentItem.workspace_id == workspace_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_scheduled_due(self, *, now: datetime, limit: int = 200) -> list[ContentItem]:
        """Bài đã duyệt tới giờ đăng, MỌI workspace — cho scheduler.

        Cố ý không scope theo workspace: scheduler là tiến trình nền của hệ
        thống, không chạy dưới danh nghĩa người dùng nào. Mọi đường đi từ HTTP
        vẫn phải qua `list_items` có `workspace_id` bắt buộc.

        Chỉ lấy `scheduled` — bài chưa duyệt không có đường nào lọt xuống
        publish, đây là chốt chặn trùng lặp cố ý sau state machine.
        """
        result = await self._session.execute(
            select(ContentItem)
            .where(
                ContentItem.status == ContentStatus.SCHEDULED,
                ContentItem.scheduled_at.is_not(None),
                ContentItem.scheduled_at <= now,
            )
            .order_by(ContentItem.scheduled_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_published(self, item: ContentItem, *, published_at: datetime) -> ContentItem:
        item.status = ContentStatus.PUBLISHED
        item.published_at = published_at
        await self._session.flush()
        return item

    async def list_items_in_range(
        self, *, workspace_id: UUID, start: datetime, end: datetime
    ) -> list[ContentItem]:
        """Lịch đăng — projection trên `scheduled_at`, không phải bảng riêng.

        `start` inclusive, `end` exclusive: caller truyền nguyên ngày kế tiếp nên
        bài đăng lúc 23:59:59 của ngày cuối vẫn nằm trong khoảng.
        """
        result = await self._session.execute(
            select(ContentItem)
            .where(
                ContentItem.workspace_id == workspace_id,
                ContentItem.scheduled_at.is_not(None),
                ContentItem.scheduled_at >= start,
                ContentItem.scheduled_at < end,
            )
            .order_by(ContentItem.scheduled_at)
        )
        return list(result.scalars().all())

    async def update_item(
        self,
        item: ContentItem,
        *,
        text: str | None,
        media_note: str | None,
        scheduled_at: datetime | None,
        edited_by: UUID,
    ) -> ContentItem:
        """PATCH: field `None` nghĩa là không đổi, không phải xoá về null.

        Đổi `text` thì tạo `content_item_versions` mới và tăng `version_no` —
        lịch sử phải trả lời được "ai sửa gì, lúc nào", nên không update tại chỗ.
        """
        if text is not None and text != item.text:
            item.version_no += 1
            item.text = text
            self._session.add(
                ContentItemVersion(
                    content_item_id=item.id,
                    version_no=item.version_no,
                    text=text,
                    edited_by=edited_by,
                    edited_at=datetime.now(UTC),
                )
            )
        if media_note is not None:
            item.media_note = media_note
        if scheduled_at is not None:
            item.scheduled_at = scheduled_at
        await self._session.flush()
        return item

    async def list_versions(self, item_id: UUID) -> list[ContentItemVersion]:
        result = await self._session.execute(
            select(ContentItemVersion)
            .where(ContentItemVersion.content_item_id == item_id)
            .order_by(ContentItemVersion.version_no)
        )
        return list(result.scalars().all())

    async def set_item_status(
        self,
        item: ContentItem,
        *,
        status: ContentStatus,
        approved_by: UUID | None = None,
        scheduled_at: datetime | None = None,
    ) -> ContentItem:
        item.status = status
        if approved_by is not None:
            item.approved_by = approved_by
            item.approved_at = datetime.now(UTC)
        if scheduled_at is not None:
            item.scheduled_at = scheduled_at
        await self._session.flush()
        return item
