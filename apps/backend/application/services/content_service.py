"""Use case cho /content — tạo job, đọc job/item. Sinh draft nằm ở ContentEngine.

Tách khỏi `ContentEngine` vì hai thứ chạy ở process khác nhau: service này chạy
trong API request (nhanh, chỉ ghi DB + enqueue), engine chạy trong worker (gọi
LLM, có thể mất hàng chục giây).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.job_queue import JobQueue
from core.alerts import Alert, AlertSink, LoggingAlertSink
from core.enums import Channel, ContentStatus
from core.request_context import get_request_id
from domain.models.content import ContentItem, ContentJob
from domain.policies import quota


class ContentJobNotFound(Exception):
    pass


class WorkspaceNotFound(Exception):
    pass


@dataclass
class CreatedJob:
    job: ContentJob
    #: False khi idempotency key trùng — job cũ được trả lại, không enqueue lần hai.
    created: bool


class SubscriptionExpired(Exception):
    """Gói cước hoặc hạn dùng thử của workspace đã hết."""


class ContentService:
    def __init__(
        self,
        *,
        content: ContentRepository,
        queue: JobQueue,
        workspaces: WorkspaceRepository,
        events: EventLogRepository,
        alerts: AlertSink | None = None,
    ) -> None:
        self._content = content
        self._queue = queue
        self._workspaces = workspaces
        self._events = events
        self._alerts = alerts or LoggingAlertSink()

    async def quota_status(
        self, *, workspace_id: UUID, now: datetime | None = None
    ) -> quota.QuotaStatus:
        now = now or datetime.now(UTC)
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFound()
        used = await self._events.tokens_used_since(
            workspace_id=workspace_id, since=quota.month_start_utc(now)
        )
        return quota.evaluate(plan=workspace.plan, used=used, now=now)

    async def create_job(
        self,
        *,
        workspace_id: UUID,
        raw_inputs: list[dict],
        idempotency_key: str | None,
        now: datetime | None = None,
    ) -> CreatedJob:
        """`idempotency_key` từ header `Idempotency-Key`.

        Không có key thì mỗi request là một job mới — nghĩa là bấm hai lần sẽ tốn
        hai lần tiền LLM. Frontend nên luôn gửi key để chặn double-submit.

        Quota kiểm **trước khi** tạo job và enqueue, tức trước khi worker gọi LLM.
        Kiểm sau khi enqueue thì tiền đã tiêu rồi mới báo "hết quota" — vô nghĩa.
        """
        now_dt = now or datetime.now(UTC)
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFound()

        from domain.policies import subscription

        sub_state = subscription.state_for(
            plan=workspace.plan,
            trial_ends_at=workspace.trial_ends_at,
            paid_until=workspace.paid_until,
            now=now_dt,
        )
        if not sub_state.is_active:
            raise SubscriptionExpired(
                "Hạn dùng thử hoặc gói cước đã hết. Vui lòng nâng cấp gói cước để tiếp tục."
            )

        status = await self.quota_status(workspace_id=workspace_id, now=now_dt)

        if status.exceeded:
            await self._alerts.send(
                Alert(
                    type="quota.exceeded",
                    severity="critical",
                    summary="Workspace đã vượt quota token tháng",
                    workspace_id=str(workspace_id),
                    fields={
                        "used": status.used,
                        "limit": status.limit,
                        "remaining": status.remaining,
                    },
                )
            )
            raise quota.QuotaExceeded(
                used=status.used, limit=status.limit, resets_at=status.resets_at
            )
        if status.near_limit:
            await self._alerts.send(
                Alert(
                    type="quota.near_limit",
                    severity="warning",
                    summary="Workspace gần chạm quota token tháng",
                    workspace_id=str(workspace_id),
                    fields={
                        "used": status.used,
                        "limit": status.limit,
                        "remaining": status.remaining,
                    },
                )
            )

        key = idempotency_key or str(uuid.uuid4())
        job, created = await self._content.create_job(
            workspace_id=workspace_id, raw_inputs=raw_inputs, idempotency_key=key
        )
        if created:
            self._queue.enqueue_generate_drafts(
                workspace_id=workspace_id, job_id=job.id, request_id=get_request_id()
            )
        return CreatedJob(job=job, created=created)

    async def get_job(self, *, workspace_id: UUID, job_id: UUID) -> ContentJob:
        job = await self._content.get_job(workspace_id=workspace_id, job_id=job_id)
        if job is None:
            raise ContentJobNotFound()
        return job

    async def list_items_for_job(self, job_id: UUID) -> list[ContentItem]:
        return await self._content.list_items_for_job(job_id)

    async def get_item(self, *, workspace_id: UUID, item_id: UUID) -> ContentItem:
        item = await self._content.get_item(workspace_id=workspace_id, item_id=item_id)
        if item is None:
            raise ContentJobNotFound()
        return item

    async def list_items(
        self,
        *,
        workspace_id: UUID,
        status: ContentStatus | None,
        channel: Channel | None,
        limit: int,
        offset: int,
    ) -> tuple[list[ContentItem], int]:
        return await self._content.list_items(
            workspace_id=workspace_id,
            status=status,
            channel=channel,
            limit=limit,
            offset=offset,
        )
