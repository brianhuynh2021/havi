"""Repository cho `VideoPublishAttempt`."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.enums import Channel, PublishFailureKind, VideoPublishAttemptStatus
from domain.models.video_publish import VideoPublishAttempt


class DuplicatePublishAttempt(Exception):
    """Job này đã có một lần gửi còn sống. Không tạo lần thứ hai.

    Ném ra từ ràng buộc unique của Postgres chứ không từ một lần SELECT trước
    đó: SELECT rồi INSERT có khe hở giữa hai câu lệnh, và khe hở đó đúng bằng
    khoảng cách giữa hai lần bấm nút.
    """


class VideoPublishRepository:
    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session

    async def start_attempt(
        self,
        *,
        workspace_id: UUID,
        video_post_id: UUID,
        channel: Channel,
        idempotency_key: str,
    ) -> VideoPublishAttempt:
        attempt = VideoPublishAttempt(
            workspace_id=workspace_id,
            video_post_id=video_post_id,
            channel=channel,
            idempotency_key=idempotency_key,
            status=VideoPublishAttemptStatus.PENDING,
        )
        self._session.add(attempt)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicatePublishAttempt(
                f"Video {video_post_id} đã có một lần gửi đang chạy hoặc đã đăng."
            ) from exc
        return attempt

    async def get_live_attempt(
        self, *, video_post_id: UUID
    ) -> VideoPublishAttempt | None:
        """Lần gửi còn sống (`pending` hoặc `published`) của job, nếu có."""
        res = await self._session.execute(
            select(VideoPublishAttempt).where(
                VideoPublishAttempt.video_post_id == video_post_id,
                VideoPublishAttempt.status.in_(
                    [VideoPublishAttemptStatus.PENDING, VideoPublishAttemptStatus.PUBLISHED]
                ),
            )
        )
        return res.scalars().first()

    async def list_needing_reconciliation(
        self, *, limit: int = 20
    ) -> list[VideoPublishAttempt]:
        res = await self._session.execute(
            select(VideoPublishAttempt)
            .where(VideoPublishAttempt.status == VideoPublishAttemptStatus.AMBIGUOUS)
            .order_by(VideoPublishAttempt.created_at)
            .limit(limit)
        )
        return list(res.scalars().all())

    async def mark_published(
        self,
        attempt: VideoPublishAttempt,
        *,
        external_post_id: str,
        permalink_url: str | None = None,
    ) -> VideoPublishAttempt:
        attempt.status = VideoPublishAttemptStatus.PUBLISHED
        attempt.external_post_id = external_post_id
        attempt.permalink_url = permalink_url
        attempt.settled_at = datetime.now(UTC)
        attempt.error_message = None
        await self._session.flush()
        return attempt

    async def mark_failed(
        self,
        attempt: VideoPublishAttempt,
        *,
        kind: PublishFailureKind,
        error_message: str,
    ) -> VideoPublishAttempt:
        attempt.status = VideoPublishAttemptStatus.FAILED
        attempt.failure_kind = kind
        attempt.error_message = error_message[:1000]
        attempt.settled_at = datetime.now(UTC)
        await self._session.flush()
        return attempt

    async def mark_ambiguous(
        self,
        attempt: VideoPublishAttempt,
        *,
        error_message: str,
        external_post_id: str | None = None,
    ) -> VideoPublishAttempt:
        """Đã gửi, mất dấu kết quả.

        Giữ nguyên `external_post_id` nếu nền tảng đã cấp: đó là manh mối duy
        nhất để đối soát. Không có nó thì chỉ còn cách dò danh sách video của
        Trang, và đó là lúc dễ nhầm sang video khác nhất.
        """
        attempt.status = VideoPublishAttemptStatus.AMBIGUOUS
        attempt.failure_kind = PublishFailureKind.AMBIGUOUS_OUTCOME
        attempt.error_message = error_message[:1000]
        if external_post_id:
            attempt.external_post_id = external_post_id
        await self._session.flush()
        return attempt

    async def bump_reconcile(self, attempt: VideoPublishAttempt) -> int:
        attempt.reconcile_attempts += 1
        await self._session.flush()
        return attempt.reconcile_attempts
