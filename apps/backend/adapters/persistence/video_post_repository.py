"""Repository cho `VideoPost` — clip đã tải lên, chờ duyệt rồi đăng.

Mọi cú đổi trạng thái đi qua `_transition`, và `_transition` gọi
`assert_transition`. Đó là chỗ duy nhất trong tầng dữ liệu được gán
`post.status`, nên không có đường nào ghi một trạng thái sai vào DB mà không
ném lỗi trước.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import Channel, VideoPostStatus
from domain.models.video_post import VideoPost
from domain.policies.video_job_state import assert_transition


class VideoPostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workspace_id: UUID,
        source_media_id: UUID,
        source_object_key: str,
        caption: str = "",
        channel: Channel = Channel.REELS,
    ) -> VideoPost:
        """Clip vào thẳng `READY_FOR_REVIEW` — không có bước dựng nào ở giữa."""
        post = VideoPost(
            workspace_id=workspace_id,
            source_media_id=source_media_id,
            source_object_key=source_object_key,
            caption=caption,
            channel=channel,
            status=VideoPostStatus.READY_FOR_REVIEW,
        )
        self._session.add(post)
        await self._session.flush()
        return post

    async def get(self, *, workspace_id: UUID, post_id: UUID) -> VideoPost | None:
        result = await self._session.execute(
            select(VideoPost).where(
                VideoPost.id == post_id,
                VideoPost.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, post_id: UUID) -> VideoPost | None:
        """Dùng ở worker, nơi chỉ có `post_id` chứ chưa có workspace."""
        result = await self._session.execute(select(VideoPost).where(VideoPost.id == post_id))
        return result.scalar_one_or_none()

    async def list_for_workspace(
        self,
        *,
        workspace_id: UUID,
        status: VideoPostStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[VideoPost], int]:
        conditions = [VideoPost.workspace_id == workspace_id]
        if status is not None:
            conditions.append(VideoPost.status == status)

        total = await self._session.scalar(
            select(func.count()).select_from(VideoPost).where(*conditions)
        )
        result = await self._session.execute(
            select(VideoPost)
            .where(*conditions)
            .order_by(VideoPost.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    async def transition(
        self,
        post: VideoPost,
        target: VideoPostStatus,
        *,
        error_message: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> VideoPost:
        """Đổi trạng thái sau khi kiểm bảng chuyển. Ném nếu cú nhảy không hợp lệ."""
        assert_transition(post.status, target)
        post.status = target
        # Lỗi cũ phải biến mất khi rời nhánh lỗi, nếu không UI hiện một câu báo
        # lỗi từ lần thử trước bên cạnh một video đã đăng thành công.
        post.error_message = error_message[:1000] if error_message else None
        if scheduled_at is not None:
            post.scheduled_at = scheduled_at
        if target == VideoPostStatus.PUBLISHED:
            post.published_at = datetime.now(UTC)
        await self._session.flush()
        return post

    async def list_due(self, *, now: datetime | None = None, limit: int = 20) -> list[VideoPost]:
        """Video đã duyệt và đã tới giờ. Worker quét bảng, không nhận id qua message.

        Chọn bằng truy vấn chứ không bằng payload của Celery: một message bị
        giao lại hai lần sẽ thành hai lượt gửi cùng một clip, và lớp chặn trùng
        ở `video_publish_attempts` tuy đỡ được nhưng lẽ ra không nên bị chạm tới.
        """
        moment = now or datetime.now(UTC)
        result = await self._session.execute(
            select(VideoPost)
            .where(
                VideoPost.status == VideoPostStatus.APPROVED,
                # `scheduled_at IS NULL` = duyệt để gửi ngay.
                (VideoPost.scheduled_at.is_(None)) | (VideoPost.scheduled_at <= moment),
            )
            .order_by(VideoPost.scheduled_at.asc().nulls_first())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cancel(self, *, workspace_id: UUID, post_id: UUID) -> bool:
        post = await self.get(workspace_id=workspace_id, post_id=post_id)
        if not post:
            return False
        # Đã gửi đi rồi thì không huỷ được — huỷ ở đây chỉ xoá dấu vết phía Havi
        # chứ không gỡ bài khỏi Trang, và như vậy là nói dối chủ tiệm.
        if VideoPostStatus.CANCELLED not in _allowed_from(post.status):
            return False
        await self.transition(post, VideoPostStatus.CANCELLED)
        return True


def _allowed_from(status: VideoPostStatus) -> frozenset[VideoPostStatus]:
    from domain.policies.video_job_state import ALLOWED_TRANSITIONS

    return ALLOWED_TRANSITIONS.get(status, frozenset())
