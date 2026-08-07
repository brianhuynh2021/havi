"""Use case cho /content — tạo job, đọc job/item. Sinh draft nằm ở ContentEngine.

Tách khỏi `ContentEngine` vì hai thứ chạy ở process khác nhau: service này chạy
trong API request (nhanh, chỉ ghi DB + enqueue), engine chạy trong worker (gọi
LLM, có thể mất hàng chục giây).
"""

import uuid
from dataclasses import dataclass
from uuid import UUID

from adapters.persistence.content_repository import ContentRepository
from application.services.job_queue import JobQueue
from core.enums import Channel, ContentStatus
from domain.models.content import ContentItem, ContentJob


class ContentJobNotFound(Exception):
    pass


@dataclass
class CreatedJob:
    job: ContentJob
    #: False khi idempotency key trùng — job cũ được trả lại, không enqueue lần hai.
    created: bool


class ContentService:
    def __init__(self, *, content: ContentRepository, queue: JobQueue) -> None:
        self._content = content
        self._queue = queue

    async def create_job(
        self,
        *,
        workspace_id: UUID,
        raw_inputs: list[dict],
        idempotency_key: str | None,
    ) -> CreatedJob:
        """`idempotency_key` từ header `Idempotency-Key`.

        Không có key thì mỗi request là một job mới — nghĩa là bấm hai lần sẽ tốn
        hai lần tiền LLM. Frontend nên luôn gửi key để chặn double-submit.
        """
        key = idempotency_key or str(uuid.uuid4())
        job, created = await self._content.create_job(
            workspace_id=workspace_id, raw_inputs=raw_inputs, idempotency_key=key
        )
        if created:
            self._queue.enqueue_generate_drafts(workspace_id=workspace_id, job_id=job.id)
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
