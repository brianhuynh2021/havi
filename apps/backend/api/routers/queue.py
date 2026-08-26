"""/queue — hàng đợi việc: bốn nguồn, một danh sách.

Đây là màn làm việc chính của người trực kênh. Trước đó, để biết hôm nay phải làm
gì, họ phải đi qua bốn chỗ: Hội thoại xem tin nhắn, Nội dung xem nháp chờ duyệt,
Lịch đăng xem bài nào hỏng, Kênh kết nối xem có kênh nào mất quyền. Bốn chỗ trong
Havi — sau khi đã thay được năm tab trình duyệt. Router này gộp chúng lại.

Ghép ở tầng router chứ không ở một service mới: bốn nguồn thuộc bốn bounded
context khác nhau, và một service "queue" biết cả bốn repository sẽ trở thành chỗ
mọi thứ chảy vào. Thứ tự ưu tiên — phần duy nhất có luật nghiệp vụ — nằm ở
`domain/policies/work_queue.py` và test được độc lập.
"""

from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.db import DbSessionDep
from adapters.persistence.inbox_repository import InboxRepository
from adapters.persistence.publish_repository import PublishRepository
from api.deps import WorkspaceDep
from core.enums import ConnectionStatus, ContentStatus, PublishStatus
from core.schemas import AssignRequest, ResponseMetrics, WorkItem, WorkQueue
from domain.models.user import User
from domain.policies import platform_links
from domain.policies.work_queue import WorkKind, priority_for

router = APIRouter(prefix="/queue", tags=["queue"])

#: Cắt bớt phần đuôi để một workspace tồn đọng hàng nghìn tin không làm màn làm
#: việc tải chậm. `total` vẫn trả số thật, nên người dùng biết mình đang xem một
#: phần — im lặng cắt rồi hiện như thể đó là tất cả mới là chỗ sai.
QUEUE_LIMIT = 200


def _truncate(text: str, length: int = 140) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= length else f"{cleaned[:length]}…"


@router.get("", response_model=WorkQueue)
async def work_queue(workspace_id: WorkspaceDep, session: DbSessionDep) -> WorkQueue:
    """Mọi việc đang mở, xếp theo thiệt hại khi bỏ sót rồi tới thời gian chờ."""
    items: list[WorkItem] = []

    # 1. Kênh mất quyền — chặn mọi việc khác, nên lên đầu.
    for connection in await ConnectionRepository(session).list_for_workspace(workspace_id):
        if connection.status is ConnectionStatus.CONNECTED:
            continue
        items.append(
            WorkItem(
                kind=WorkKind.CONNECTION.value,
                id=connection.id,
                title=f"Kênh {connection.platform.value} cần xác thực lại",
                detail=(
                    connection.external_account_name
                    or "Nối lại để Havi đăng và nhận tin được"
                ),
                channel=connection.platform.value,
                priority=priority_for(kind=WorkKind.CONNECTION),
                waiting_since=connection.created_at,
                href="/app/connections",
            )
        )

    # 2. Hộp thư — tin nhắn, bình luận, đánh giá còn phải trả lời.
    for item, assignee_name in await InboxRepository(session).list_open(
        workspace_id=workspace_id, limit=QUEUE_LIMIT
    ):
        items.append(
            WorkItem(
                kind=WorkKind.INBOX.value,
                id=item.id,
                title=item.author_name,
                detail=_truncate(item.content),
                channel=item.platform.value,
                category=item.category,
                priority=priority_for(kind=WorkKind.INBOX, category=item.category),
                waiting_since=item.created_at,
                assigned_to_user_id=item.assigned_to_user_id,
                assigned_to_name=assignee_name,
                platform_url=platform_links.inbox_item_url(
                    platform=item.platform,
                    item_type=item.type,
                    external_message_id=item.external_message_id,
                ),
                href="/app/inbox",
            )
        )

    # 3. Bài đăng thất bại — mất âm thầm, không ai phàn nàn.
    publishes = PublishRepository(session)
    for job_status in (PublishStatus.FAILED, PublishStatus.DEAD_LETTER):
        for job in await publishes.list_for_workspace(
            workspace_id=workspace_id, status=job_status
        ):
            items.append(
                WorkItem(
                    kind=WorkKind.PUBLISH_FAILURE.value,
                    id=job.id,
                    title="Bài chưa lên được kênh",
                    detail=job.failure_detail or "Chưa rõ lý do — mở để xem chi tiết",
                    channel=job.channel.value,
                    priority=priority_for(kind=WorkKind.PUBLISH_FAILURE),
                    waiting_since=job.scheduled_at,
                    href="/app/calendar",
                )
            )

    # 4. Nháp chờ duyệt — công việc bị chặn, nhưng chưa mất gì.
    drafts, _ = await ContentRepository(session).list_items(
        workspace_id=workspace_id, status=ContentStatus.PENDING_APPROVAL, limit=QUEUE_LIMIT
    )
    for draft in drafts:
        items.append(
            WorkItem(
                kind=WorkKind.APPROVAL.value,
                id=draft.id,
                title="Bản nháp chờ duyệt",
                detail=_truncate(draft.text),
                channel=draft.channel.value,
                priority=priority_for(kind=WorkKind.APPROVAL),
                waiting_since=draft.created_at,
                href="/app/content",
            )
        )

    # Ưu tiên trước, rồi tới ai chờ lâu nhất. Chờ lâu nhất lên trước trong cùng
    # một mức: một khách đợi từ sáng không được xếp sau khách vừa nhắn.
    items.sort(key=lambda item: (item.priority, item.waiting_since))
    return WorkQueue(items=items[:QUEUE_LIMIT], total=len(items))


@router.post("/inbox/{item_id}/assign", response_model=WorkItem)
async def assign_inbox_item(
    item_id: UUID,
    payload: AssignRequest,
    workspace_id: WorkspaceDep,
    session: DbSessionDep,
) -> WorkItem:
    """Nhận việc, hoặc trả lại hàng đợi khi `user_id` là `null`.

    Không kiểm "người này có trong workspace không" ở đây vì `assigned_to_user_id`
    có khoá ngoại `ON DELETE SET NULL` sang `users`, và giá trị chỉ dùng để hiện
    tên — gán sai thì hậu quả là một cái tên lạ trên thẻ việc, không phải một lỗ
    quyền. Ai được nhận việc gì là câu hỏi của lần sau.
    """
    repo = InboxRepository(session)
    item = await repo.get(workspace_id=workspace_id, item_id=item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không có việc này trong workspace")

    updated = await repo.assign(item, user_id=payload.user_id)

    # Tên người nhận lấy từ database, không lấy từ JWT: người gán có thể gán cho
    # người khác, và một token chỉ biết tên của chính chủ nó.
    assignee_name: str | None = None
    if updated.assigned_to_user_id is not None:
        row = await session.execute(
            select(User.name).where(User.id == updated.assigned_to_user_id)
        )
        assignee_name = row.scalar_one_or_none()
    return WorkItem(
        kind=WorkKind.INBOX.value,
        id=updated.id,
        title=updated.author_name,
        detail=_truncate(updated.content),
        channel=updated.platform.value,
        category=updated.category,
        priority=priority_for(kind=WorkKind.INBOX, category=updated.category),
        waiting_since=updated.created_at,
        assigned_to_user_id=updated.assigned_to_user_id,
        assigned_to_name=assignee_name,
        platform_url=platform_links.inbox_item_url(
            platform=updated.platform,
            item_type=updated.type,
            external_message_id=updated.external_message_id,
        ),
        href="/app/inbox",
    )


@router.get("/response-metrics", response_model=ResponseMetrics)
async def response_metrics(
    workspace_id: WorkspaceDep,
    session: DbSessionDep,
    start: date = Query(...),
    end: date = Query(...),
) -> ResponseMetrics:
    """Tổn thất tránh được trong kỳ — thời gian phản hồi và việc bị bỏ sót."""
    if end < start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "`end` phải sau `start`")

    range_start = datetime.combine(start, datetime.min.time(), UTC)
    range_end = datetime.combine(end, datetime.max.time(), UTC)
    now = datetime.now(UTC)

    metrics = await InboxRepository(session).response_metrics(
        workspace_id=workspace_id, start=range_start, end=range_end, now=now
    )
    return ResponseMetrics(window_start=range_start, window_end=range_end, **metrics)
