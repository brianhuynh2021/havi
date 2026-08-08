"""Publish service — ghép content item, kết nối nền tảng và adapter đăng bài.

Đây là nơi cưỡng chế nguyên tắc #1 và #8 (ROADMAP §1): chỉ bài đã duyệt mới được
đăng, và retry không được tạo bài trùng.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.publish_repository import PublishRepository
from core.enums import (
    Channel,
    ConnectionStatus,
    Platform,
    PublishFailureKind,
)
from core.token_crypto import TokenDecryptionFailed
from domain.models.publish import PublishJob
from domain.ports.publisher import (
    AuthPermissionError,
    PublisherPort,
    PublishError,
    PublishRequest,
)

logger = logging.getLogger(__name__)

#: Kênh nào đăng qua nền tảng nào. Chỉ Facebook có adapter thật ở pilot.
CHANNEL_TO_PLATFORM: dict[Channel, Platform] = {
    Channel.FACEBOOK_PAGE: Platform.FACEBOOK,
    Channel.ZALO_OA: Platform.ZALO_OA,
    Channel.GOOGLE_BUSINESS: Platform.GOOGLE_BUSINESS,
}


@dataclass
class DispatchResult:
    enqueued: int
    skipped: int


class PublishService:
    def __init__(
        self,
        *,
        content: ContentRepository,
        connections: ConnectionRepository,
        publishes: PublishRepository,
        publishers: dict[Channel, PublisherPort],
    ) -> None:
        self._content = content
        self._connections = connections
        self._publishes = publishes
        self._publishers = publishers

    async def dispatch_due(self, *, now: datetime | None = None) -> DispatchResult:
        """Scheduler: tìm bài đã duyệt tới giờ đăng và xếp vào hàng đợi.

        Chỉ lấy `scheduled` — `pending_approval` chưa được chủ tiệm duyệt thì
        không có đường nào lọt xuống publish. Đây là chốt chặn thứ hai sau state
        machine, cố ý trùng lặp vì đăng nhầm bài chưa duyệt là lỗi không sửa được.

        `enqueue` idempotent nên scheduler chạy lại (quét mỗi 5 phút, hoặc chạy
        chồng khi deploy) không sinh job trùng.
        """
        now = now or datetime.now(UTC)
        items = await self._content.list_scheduled_due(now=now, limit=200)

        enqueued = skipped = 0
        for item in items:
            if item.scheduled_at is None:
                skipped += 1
                continue
            scheduled = item.scheduled_at
            if scheduled.tzinfo is None:
                scheduled = scheduled.replace(tzinfo=UTC)

            _, created = await self._publishes.enqueue(
                workspace_id=item.workspace_id,
                content_item_id=item.id,
                channel=item.channel,
                scheduled_at=scheduled,
            )
            enqueued += int(created)
            skipped += int(not created)

        return DispatchResult(enqueued=enqueued, skipped=skipped)

    async def run_job(self, job: PublishJob) -> PublishJob:
        """Worker: đăng một job đã được `claim_due` khoá.

        Mọi lỗi đều đi qua `mark_failed` để repository quyết định retry hay
        dead-letter — service không tự quyết, tránh hai chỗ cùng cài luật retry
        rồi lệch nhau.
        """
        item = await self._content.get_item(
            workspace_id=job.workspace_id, item_id=job.content_item_id
        )
        if item is None:
            return await self._publishes.mark_failed(
                job,
                kind=PublishFailureKind.VALIDATION_PERMANENT,
                detail="Không tìm thấy bài — có thể đã bị xoá",
            )

        publisher = self._publishers.get(job.channel)
        if publisher is None:
            return await self._publishes.mark_failed(
                job,
                kind=PublishFailureKind.VALIDATION_PERMANENT,
                detail=f"Chưa hỗ trợ đăng lên {job.channel.value}",
            )

        platform = CHANNEL_TO_PLATFORM.get(job.channel)
        connection = (
            await self._connections.get(workspace_id=job.workspace_id, platform=platform)
            if platform
            else None
        )
        if connection is None or connection.status is not ConnectionStatus.CONNECTED:
            return await self._publishes.mark_failed(
                job,
                kind=PublishFailureKind.AUTH_PERMISSION,
                detail="Kênh chưa nối hoặc đã mất kết nối — chị nối lại giúp em nhé",
            )

        try:
            access_token = self._connections.read_access_token(connection)
        except TokenDecryptionFailed:
            # Sai khoá mã hoá: token trong DB vô dụng. Đánh dấu kết nối hỏng để
            # UI bắt nối lại, thay vì retry mãi một thứ không giải mã được.
            await self._connections.mark_unusable(
                connection,
                status=ConnectionStatus.REVOKED,
                reason="Không giải mã được token — cần nối lại kênh",
            )
            return await self._publishes.mark_failed(
                job,
                kind=PublishFailureKind.AUTH_PERMISSION,
                detail="Không giải mã được token nền tảng",
            )

        try:
            result = await publisher.publish(
                PublishRequest(
                    text=item.text,
                    external_account_id=connection.external_account_id,
                    idempotency_key=job.idempotency_key,
                ),
                access_token=access_token,
            )
        except AuthPermissionError as exc:
            # Mất quyền ở phía nền tảng — đánh dấu luôn kết nối, không chỉ job.
            # Nếu không, mọi bài sau đó cũng hỏng mà UI vẫn hiện chấm xanh.
            await self._connections.mark_unusable(
                connection, status=ConnectionStatus.EXPIRED, reason=exc.detail
            )
            return await self._publishes.mark_failed(
                job, kind=exc.kind, detail=exc.detail
            )
        except PublishError as exc:
            return await self._publishes.mark_failed(
                job, kind=exc.kind, detail=exc.detail
            )

        await self._content.mark_published(item, published_at=result.published_at)
        return await self._publishes.mark_succeeded(
            job,
            external_post_id=result.external_post_id,
            published_at=result.published_at,
        )

    async def run_due(self, *, now: datetime | None = None, limit: int = 20) -> list[PublishJob]:
        """Nhận job đến hạn rồi chạy từng cái. Một job hỏng không làm hỏng cả lô."""
        now = now or datetime.now(UTC)
        jobs = await self._publishes.claim_due(now=now, limit=limit)
        for job in jobs:
            try:
                await self.run_job(job)
            except Exception:
                logger.exception("publish job %s lỗi ngoài dự kiến", job.id)
                await self._publishes.mark_failed(
                    job,
                    kind=PublishFailureKind.TEMPORARY,
                    detail="Lỗi hệ thống ngoài dự kiến",
                )
        return jobs
