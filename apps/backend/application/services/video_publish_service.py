"""Duyệt → đăng → xác minh cho clip chủ tiệm đã tải lên.

Luật trung tâm: **không có đường nào tới `PUBLISHED` mà không đọc lại nền tảng.**
`finish` trả 200 chỉ nghĩa là Facebook nhận job; Reels xử lý bất đồng bộ và vẫn
có thể hỏng sau đó. Trước khi có tầng này, "đã đăng" là suy đoán từ một mã HTTP.

Luật thứ hai: mất dấu thì **đối soát, không gửi lại**. Mọi lỗi xảy ra sau khi
Facebook đã cấp `video_id` đều mơ hồ — có thể video đã lên Trang. Gửi lại ở đó
là cách chắc chắn nhất để tạo hai Reels giống hệt nhau trên Trang của khách.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from adapters.persistence.video_post_repository import VideoPostRepository
from adapters.persistence.video_publish_repository import (
    DuplicatePublishAttempt,
    VideoPublishRepository,
)
from core.enums import Channel, ConnectionStatus, PublishFailureKind, VideoPostStatus
from domain.models.video_post import VideoPost
from domain.models.video_publish import VideoPublishAttempt
from domain.policies.video_job_state import is_publishable
from domain.ports.publisher import (
    AmbiguousPublishError,
    PublishError,
    PublishRequest,
    ReelStatus,
)

logger = logging.getLogger("havi.video_publish")

#: Ngưng đối soát sau ngần này lượt. Video vẫn ở `PENDING_RECONCILIATION` để
#: người thật xem — thà treo có dấu vết còn hơn tự kết luận rồi kết luận sai.
MAX_RECONCILE_ATTEMPTS = 8

#: Đã gửi đi rồi — mọi yêu cầu đăng tiếp phải bị từ chối kèm lý do rõ ràng.
_ALREADY_SENT = frozenset(
    {
        VideoPostStatus.PUBLISHING,
        VideoPostStatus.VERIFYING,
        VideoPostStatus.PUBLISHED,
        VideoPostStatus.PENDING_RECONCILIATION,
    }
)


class VideoNotReadyForPublish(Exception):
    """Video chưa được duyệt, hoặc đã gửi đi rồi."""


class ChannelNotConnected(Exception):
    """Chưa nối Trang, hoặc kết nối đã mất hiệu lực."""


@dataclass
class PublishOutcome:
    post: VideoPost
    attempt: VideoPublishAttempt | None
    external_post_id: str | None = None
    permalink_url: str | None = None


class VideoPublishService:
    def __init__(
        self,
        *,
        posts: VideoPostRepository,
        attempts: VideoPublishRepository,
        connections,  # noqa: ANN001 — ConnectionService, tránh vòng import
        publisher,  # noqa: ANN001 — FacebookPublisher (có `verify_reel`)
        signed_url_for,  # noqa: ANN001 — Callable[[VideoPost], str] URL đã ký của clip
    ) -> None:
        self._posts = posts
        self._attempts = attempts
        self._connections = connections
        self._publisher = publisher
        self._signed_url_for = signed_url_for

    # ---------------------------------------------------------------- duyệt

    async def approve(
        self, *, workspace_id: UUID, post_id: UUID, scheduled_at: datetime | None = None
    ) -> VideoPost:
        """`READY_FOR_REVIEW` → `APPROVED`. Đây là chỗ con người xác nhận.

        Không có cổng "kiểm tra chất lượng" ở đây, và đó là chủ ý: Havi không
        dựng video nên không có gì để tự chấm. Ràng buộc kênh (khung hình, thời
        lượng, tiếng) đã kiểm lúc upload — kiểm lại ở đây chỉ làm chậm cú bấm mà
        không phát hiện thêm gì, vì file không đổi giữa hai thời điểm.

        Cổng thật sự nằm ở bảng chuyển trạng thái: nó chặn duyệt lại một video
        đã gửi đi.

        `scheduled_at=None` nghĩa là gửi ngay ở lượt worker kế tiếp. Có giờ thì
        video nằm ở `APPROVED` cho tới lúc đó — cùng cách bài viết hoạt động,
        nên "chuẩn bị cả tuần nội dung trong một buổi" áp dụng được cho cả hai.
        """
        post = await self._require(workspace_id, post_id)

        if post.status in _ALREADY_SENT:
            raise VideoNotReadyForPublish(
                "Video này đã được gửi đăng rồi — không duyệt lại để tránh đăng trùng."
            )

        # Kiểm kết nối ngay lúc duyệt, không đợi worker: chủ tiệm bấm duyệt rồi
        # đi làm việc khác, và một lỗi "chưa nối Trang" phát hiện ở worker thì
        # không ai đọc.
        await self._resolve_connection(workspace_id)

        return await self._posts.transition(
            post, VideoPostStatus.APPROVED, scheduled_at=scheduled_at
        )

    # ----------------------------------------------------------------- đăng

    async def publish(
        self, *, workspace_id: UUID, post_id: UUID, channel: Channel | None = None
    ) -> PublishOutcome:
        """`APPROVED` → `PUBLISHING` → `VERIFYING` → `PUBLISHED`.

        Không nhảy tắt bước nào. Mỗi bước chỉ chuyển sau khi việc tương ứng đã
        thực sự xảy ra.
        """
        post = await self._require(workspace_id, post_id)
        # Kênh đích chốt lúc tạo bản ghi; tham số chỉ để ghi đè trong test.
        channel = channel or post.channel

        if not is_publishable(post.status):
            # Phân biệt "chưa tới lượt" với "đã qua lượt": hai tình huống này cần
            # hai câu trả lời khác hẳn nhau, và nhầm chúng là cách người dùng bấm
            # đăng lần nữa vì tưởng lần đầu chưa ăn.
            if post.status in _ALREADY_SENT:
                raise VideoNotReadyForPublish(await self._already_sent_message(post_id))
            raise VideoNotReadyForPublish(
                f"Video đang ở trạng thái {post.status.value}, chưa được duyệt để đăng."
            )

        access_token, page_id = await self._resolve_connection(workspace_id)

        # Khoá ở Postgres, không ở Python: hai worker cùng nhận job hay chủ tiệm
        # bấm hai lần đều dừng ở đây.
        try:
            attempt = await self._attempts.start_attempt(
                workspace_id=workspace_id,
                video_post_id=post_id,
                channel=channel,
                idempotency_key=f"video:{post_id}:{channel.value}",
            )
        except DuplicatePublishAttempt as exc:
            raise VideoNotReadyForPublish(await self._already_sent_message(post_id)) from exc

        await self._posts.transition(post, VideoPostStatus.PUBLISHING)

        request = PublishRequest(
            text=post.caption,
            media_urls=[self._signed_url_for(post)],
            external_account_id=page_id,
            idempotency_key=attempt.idempotency_key,
            channel=channel,
        )

        try:
            result = await self._publisher.publish(request, access_token=access_token)
        except AmbiguousPublishError as exc:
            # Đã gửi, mất dấu. Đây là nhánh duy nhất không được thử lại.
            await self._attempts.mark_ambiguous(attempt, error_message=str(exc))
            await self._posts.transition(
                post, VideoPostStatus.PENDING_RECONCILIATION, error_message=str(exc)
            )
            logger.warning("Video %s mất dấu sau khi gửi: %s", post_id, exc)
            return PublishOutcome(post=post, attempt=attempt)
        except PublishError as exc:
            await self._attempts.mark_failed(attempt, kind=exc.kind, error_message=str(exc))
            await self._posts.transition(post, VideoPostStatus.FAILED, error_message=str(exc))
            return PublishOutcome(post=post, attempt=attempt)

        # Nền tảng đã nhận. Chưa phải đã đăng.
        attempt.external_post_id = result.external_post_id
        await self._posts.transition(post, VideoPostStatus.VERIFYING)

        return await self._verify(post=post, attempt=attempt, access_token=access_token)

    # ------------------------------------------------------------- xác minh

    async def _verify(
        self, *, post: VideoPost, attempt: VideoPublishAttempt, access_token: str
    ) -> PublishOutcome:
        """Đọc lại nền tảng. Chỉ `published` mới được đi tiếp."""
        try:
            status: ReelStatus = await self._publisher.verify_reel(
                attempt.external_post_id, access_token=access_token
            )
        except PublishError as exc:
            # Chưa đọc được không có nghĩa là hỏng — treo lại để đối soát.
            message = f"Chưa đọc được trạng thái bài: {exc}"
            await self._attempts.mark_ambiguous(
                attempt, error_message=message, external_post_id=attempt.external_post_id
            )
            await self._posts.transition(
                post, VideoPostStatus.PENDING_RECONCILIATION, error_message=message
            )
            return PublishOutcome(post=post, attempt=attempt)

        if status.is_published:
            return await self._settle_published(post, attempt, status)

        if status.is_failed:
            message = status.error_message or f"Facebook từ chối video ({status.phase})"
            await self._attempts.mark_failed(
                attempt,
                kind=PublishFailureKind.VALIDATION_PERMANENT,
                error_message=message,
            )
            await self._posts.transition(post, VideoPostStatus.FAILED, error_message=message)
            return PublishOutcome(post=post, attempt=attempt)

        # Đang xử lý — chưa kết luận được. Để đối soát chạy lại sau.
        message = f"Facebook còn đang xử lý ({status.phase})"
        await self._attempts.mark_ambiguous(
            attempt, error_message=message, external_post_id=attempt.external_post_id
        )
        await self._posts.transition(
            post, VideoPostStatus.PENDING_RECONCILIATION, error_message=message
        )
        return PublishOutcome(post=post, attempt=attempt)

    async def due_posts(self, *, limit: int = 20) -> list[VideoPost]:
        """Video đã duyệt và đã tới giờ, để worker quét theo lịch."""
        return await self._posts.list_due(limit=limit)

    # ------------------------------------------------------------ đối soát

    async def reconcile(
        self, *, workspace_id: UUID, attempt: VideoPublishAttempt
    ) -> PublishOutcome:
        """Đi kiểm tra một lần gửi đã mất dấu. Tuyệt đối không gửi lại.

        Chỉ có hai lối ra: xác minh được là đã đăng, hoặc kết luận hỏng hẳn.
        Hết số lượt mà vẫn chưa rõ thì để nguyên cho người thật xem — treo có
        dấu vết vẫn hơn tự kết luận rồi kết luận sai.
        """
        post = await self._posts.get(workspace_id=workspace_id, post_id=attempt.video_post_id)
        if post is None:
            raise VideoNotReadyForPublish("Không tìm thấy video để đối soát")

        if not attempt.external_post_id:
            # Không có manh mối nào. Dò danh sách video của Trang là cách dễ nhầm
            # sang video khác nhất, nên dừng lại cho người thật xử.
            message = "Mất dấu hoàn toàn: nền tảng chưa kịp cấp mã video."
            await self._attempts.mark_failed(
                attempt, kind=PublishFailureKind.AMBIGUOUS_OUTCOME, error_message=message
            )
            await self._posts.transition(
                post, VideoPostStatus.FAILED_PERMANENT, error_message=message
            )
            return PublishOutcome(post=post, attempt=attempt)

        access_token, _ = await self._resolve_connection(workspace_id)
        count = await self._attempts.bump_reconcile(attempt)

        try:
            status = await self._publisher.verify_reel(
                attempt.external_post_id, access_token=access_token
            )
        except PublishError as exc:
            if count >= MAX_RECONCILE_ATTEMPTS:
                post.error_message = (
                    f"Đã đối soát {count} lượt mà chưa đọc được trạng thái: {exc}"
                )[:1000]
            return PublishOutcome(post=post, attempt=attempt)

        if status.is_published:
            return await self._settle_published(post, attempt, status)

        if status.is_failed:
            message = status.error_message or f"Facebook không đăng được video ({status.phase})"
            await self._attempts.mark_failed(
                attempt,
                kind=PublishFailureKind.VALIDATION_PERMANENT,
                error_message=message,
            )
            await self._posts.transition(
                post, VideoPostStatus.FAILED_PERMANENT, error_message=message
            )
            return PublishOutcome(post=post, attempt=attempt)

        if count >= MAX_RECONCILE_ATTEMPTS:
            post.error_message = (
                f"Đã đối soát {count} lượt, Facebook vẫn báo '{status.phase}'. "
                "Cần người kiểm tra Trang trực tiếp."
            )[:1000]
        return PublishOutcome(post=post, attempt=attempt)

    # ------------------------------------------------------------- phụ trợ

    async def _settle_published(
        self, post: VideoPost, attempt: VideoPublishAttempt, status: ReelStatus
    ) -> PublishOutcome:
        """Đường duy nhất tới `PUBLISHED` — và nó bắt đầu từ một lần đọc lại."""
        await self._attempts.mark_published(
            attempt,
            external_post_id=status.video_id,
            permalink_url=status.permalink_url,
        )
        await self._posts.transition(post, VideoPostStatus.PUBLISHED)
        return PublishOutcome(
            post=post,
            attempt=attempt,
            external_post_id=status.video_id,
            permalink_url=status.permalink_url,
        )

    async def _require(self, workspace_id: UUID, post_id: UUID) -> VideoPost:
        post = await self._posts.get(workspace_id=workspace_id, post_id=post_id)
        if post is None:
            raise VideoNotReadyForPublish(f"Không tìm thấy video {post_id}")
        return post

    async def _already_sent_message(self, post_id: UUID) -> str:
        """Câu từ chối kèm mã bài, để chủ tiệm tự vào Trang đối chiếu được."""
        existing = await self._attempts.get_live_attempt(video_post_id=post_id)
        suffix = (
            f" (mã bài {existing.external_post_id})"
            if existing and existing.external_post_id
            else ""
        )
        return f"Video này đã được gửi đăng rồi{suffix} — không gửi lại để tránh đăng trùng."

    async def _resolve_connection(self, workspace_id: UUID) -> tuple[str, str]:
        from core.enums import Platform

        connection = await self._connections.get(
            workspace_id=workspace_id, platform=Platform.FACEBOOK
        )
        if connection is None or connection.status is not ConnectionStatus.CONNECTED:
            raise ChannelNotConnected(
                "Chưa nối Trang Facebook, hoặc kết nối đã hết hạn. "
                "Vào Cài đặt → Kết nối để nối lại."
            )
        page_id = connection.external_account_id
        if not page_id:
            raise ChannelNotConnected(
                "Kết nối Facebook thiếu Page ID. Vào Cài đặt → Kết nối để nối lại."
            )
        return self._connections.read_access_token(connection), page_id
