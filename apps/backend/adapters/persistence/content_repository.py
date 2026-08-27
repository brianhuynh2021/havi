from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

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
        job_id: UUID | None,
        channel: Channel,
        kind: str,
        text: str,
        media_note: str | None,
        media_url: str | None = None,
        status: ContentStatus,
        ai_authored: bool = True,
    ) -> ContentItem:
        """`ai_authored=False` cho bài người tự viết: không ghi bản v1 của máy.

        Bài người tự dán vào không có "bản AI" nào để so, nên ghi nó thành v1 sẽ
        làm `list_ai_human_pairs` trả về cặp (chữ người viết → chữ người sửa) và
        dạy nắn giọng văn theo chính giọng người dùng — một vòng lặp học từ nhiễu.
        """
        item = ContentItem(
            workspace_id=workspace_id,
            job_id=job_id,
            channel=channel,
            kind=kind,
            text=text,
            media_note=media_note,
            media_url=media_url,
            status=status,
        )
        self._session.add(item)
        await self._session.flush()
        # Bản v1 — chính chữ AI vừa sinh — được lưu ngay tại đây.
        #
        # `update_item` ghi đè `item.text` khi có người sửa, nên nếu v1 không
        # được lưu lúc này thì bản gốc **biến mất** và không cách nào lấy lại:
        # cặp (AI viết gì → người sửa thành gì) là dữ liệu duy nhất nói lên giọng
        # thật của tiệm, và nó chỉ tồn tại nếu ta ghi trước khi bị ghi đè.
        #
        # `edited_by=None` phân biệt máy với người: mọi bản do người sửa đều
        # mang id của họ. Không cần thêm cột nào.
        if ai_authored:
            self._session.add(
                ContentItemVersion(
                    content_item_id=item.id,
                    version_no=item.version_no,
                    text=text,
                    edited_by=None,
                    edited_at=datetime.now(UTC),
                )
            )
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
        else:
            filters.append(ContentItem.status != ContentStatus.DISMISSED)
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

    async def last_published_by_channel(
        self, *, workspace_id: UUID
    ) -> dict[Channel, datetime]:
        """Lần cuối mỗi kênh có bài lên, không giới hạn cửa sổ thời gian.

        Cố ý **không** nhận `start`: câu hỏi là "bao lâu rồi chưa đăng", nên giới
        hạn cửa sổ sẽ làm một kênh im 90 ngày trông giống kênh im 8 ngày. Một
        `max()` có index trên `workspace_id` thì rẻ dù bảng dài.
        """
        rows = await self._session.execute(
            select(ContentItem.channel, func.max(ContentItem.published_at))
            .where(
                ContentItem.workspace_id == workspace_id,
                ContentItem.status == ContentStatus.PUBLISHED,
                ContentItem.published_at.is_not(None),
            )
            .group_by(ContentItem.channel)
        )
        return {channel: published_at for channel, published_at in rows.all()}

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

    async def count_drafts_generated_and_approved(
        self, *, workspace_id: UUID, start: datetime, end: datetime
    ) -> tuple[int, int]:
        """(số nháp Havi sinh ra, số nháp người dùng thật sự duyệt) trong cửa sổ.

        Hai con số này là mẫu số của kinh tế đơn vị. Chi phí LLM phát sinh cho
        **mọi** bản nháp được sinh ra, kể cả những bản bị xoá ngay; nhưng thứ đưa
        được lên kênh chỉ là những bản được duyệt. Tiệm sinh 5 nháp dùng 1 thì
        chi phí thật cho một bài lên kênh gấp 5 lần chi phí mỗi bản nháp.

        Đếm theo hai mốc thời gian khác nhau, và đó là chủ ý: nháp tính theo lúc
        được sinh (`created_at`), duyệt tính theo lúc được duyệt (`approved_at`).
        Một bản nháp sinh cuối tháng trước và duyệt đầu tháng này thuộc về hai
        kỳ khác nhau — đúng với dòng tiền, vì token đã tiêu ở kỳ trước.

        Tỷ lệ giữa hai số cũng là chỉ số chất lượng nháp: vứt càng nhiều thì
        prompt càng cần sửa, và biên lợi nhuận càng mỏng.
        """
        generated = await self._session.execute(
            select(func.count()).where(
                ContentItem.workspace_id == workspace_id,
                ContentItem.created_at >= start,
                ContentItem.created_at < end,
            )
        )
        approved = await self._session.execute(
            select(func.count()).where(
                ContentItem.workspace_id == workspace_id,
                ContentItem.approved_at.is_not(None),
                ContentItem.approved_at >= start,
                ContentItem.approved_at < end,
            )
        )
        return generated.scalar_one(), approved.scalar_one()

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
        bài đăng lúc 23:59:59 của ngày cuối vẫn nằm trong khoảng. Bỏ qua bản nháp (DRAFT).
        """
        result = await self._session.execute(
            select(ContentItem)
            .where(
                ContentItem.workspace_id == workspace_id,
                ContentItem.status != ContentStatus.DRAFT,
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
        media_url: str | None = None,
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
        if media_url is not None:
            item.media_url = None if media_url == "__NONE__" else media_url
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

    async def list_ai_human_pairs(
        self, *, workspace_id: UUID, limit: int = 20
    ) -> list[tuple[str, str]]:
        """Cặp `(chữ AI viết, chữ người sửa thành)` của một workspace, mới trước.

        Đây là dữ liệu để nắn giọng văn: chỗ chủ tiệm sửa nói rõ hơn mọi ô khai
        form, vì nó là *hành vi* chứ không phải *mô tả về mình*.

        Chỉ lấy item đã có người sửa (`version_no > 1`). Bài AI viết mà được duyệt
        nguyên văn không nằm ở đây — nó không chứa thông tin sửa chữa nào, và
        trộn vào chỉ làm loãng tín hiệu.

        `edited_by IS NULL` chọn đúng bản của máy; bản cuối là bản `version_no`
        lớn nhất, tức chữ đang được dùng thật.
        """
        ai = aliased(ContentItemVersion)
        human = aliased(ContentItemVersion)
        latest = (
            select(func.max(ContentItemVersion.version_no))
            .where(ContentItemVersion.content_item_id == ContentItem.id)
            .scalar_subquery()
        )
        result = await self._session.execute(
            select(ai.text, human.text)
            .join(ContentItem, ContentItem.id == ai.content_item_id)
            .join(human, human.content_item_id == ContentItem.id)
            .where(
                ContentItem.workspace_id == workspace_id,
                ai.version_no == 1,
                ai.edited_by.is_(None),
                human.version_no == latest,
                human.version_no > 1,
            )
            .order_by(human.edited_at.desc())
            .limit(limit)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def set_item_status(
        self,
        item: ContentItem,
        *,
        status: ContentStatus,
        approved_by: UUID | None = None,
        scheduled_at: datetime | None = None,
        clear_schedule: bool = False,
    ) -> ContentItem:
        item.status = status
        if approved_by is not None:
            item.approved_by = approved_by
            item.approved_at = datetime.now(UTC)
        if clear_schedule or status in {ContentStatus.DRAFT, ContentStatus.DISMISSED}:
            item.scheduled_at = None
        elif scheduled_at is not None:
            item.scheduled_at = scheduled_at
        await self._session.flush()
        return item
