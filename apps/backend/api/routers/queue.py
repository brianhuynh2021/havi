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

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from adapters.persistence.connection_repository import (
    PLATFORM_TO_CHANNELS,
    ConnectionRepository,
)
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.db import DbSessionDep
from adapters.persistence.inbox_repository import InboxRepository
from adapters.persistence.publish_repository import PublishRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from api.deps import WorkspaceDep
from core.enums import (
    Channel,
    ConnectionStatus,
    ContentStatus,
    InboxItemStatus,
    PublishStatus,
)
from core.schemas import (
    AssignRequest,
    BriefActivity,
    BriefGap,
    BriefSavedAction,
    BriefSilentChannel,
    MorningBrief,
    ResponseMetrics,
    WorkItem,
    WorkQueue,
)
from domain.models.user import User
from domain.policies import brief as brief_policy
from domain.policies import channel_capabilities, inbox_triage, platform_links
from domain.policies.scheduling import VIETNAM_TZ
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

    # 1. Kênh kết nối — mất quyền hoặc chưa nối kênh nào, chặn mọi việc khác nên lên đầu.
    connections = await ConnectionRepository(session).list_for_workspace(workspace_id)
    connected_live_channels: list[Channel] = []
    for connection in connections:
        if connection.status is ConnectionStatus.CONNECTED:
            for ch in PLATFORM_TO_CHANNELS.get(connection.platform, []):
                if ch in channel_capabilities.LIVE_CHANNELS:
                    connected_live_channels.append(ch)
        else:
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

    if not connected_live_channels and not any(i.kind == WorkKind.CONNECTION.value for i in items):
        from uuid import NAMESPACE_URL, uuid5
        dummy_id = uuid5(NAMESPACE_URL, f"havi:no-connection:{workspace_id}")
        items.append(
            WorkItem(
                kind=WorkKind.CONNECTION.value,
                id=dummy_id,
                title="Chưa nối kênh nào",
                detail="Chưa có kênh mạng xã hội nào được kết nối. Nối ít nhất một kênh để Havi bắt đầu hỗ trợ đăng bài và chăm sóc khách.",
                channel=None,
                priority=priority_for(kind=WorkKind.CONNECTION),
                waiting_since=datetime.now(UTC),
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

    Người được giao phải là thành viên workspace. Nếu chỉ dựa vào khoá ngoại tới
    `users`, một UUID ở workspace khác có thể làm lộ tên người đó trên thẻ việc
    và phá vỡ bất biến tenant dù bản thân tin nhắn vẫn không bị đọc chéo.
    """
    repo = InboxRepository(session)
    item = await repo.get(workspace_id=workspace_id, item_id=item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không có việc này trong workspace")

    if payload.user_id is not None and not await WorkspaceMemberRepository(session).is_member(
        workspace_id=workspace_id,
        user_id=payload.user_id,
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Người được giao không thuộc workspace",
        )

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


@router.get("/brief", response_model=MorningBrief)
async def morning_brief(
    workspace_id: WorkspaceDep,
    session: DbSessionDep,
    window_hours: int = Query(default=brief_policy.DEFAULT_WINDOW_HOURS, ge=1, le=168),
) -> MorningBrief:
    """Bản tin buổi sáng — màn của chủ, không phải hàng đợi của nhân viên.

    Không gọi LLM: mọi con số đếm từ dữ liệu Havi đã sở hữu, nên không có chỗ nào
    để bịa. Thứ Havi chưa đo được thì **vắng mặt**, không được đoán — xem
    `domain/policies/brief.py`.
    """
    now = datetime.now(UTC)
    start = brief_policy.window_start(now=now, hours=window_hours)

    contents = ContentRepository(session)
    inboxes = InboxRepository(session)
    publishes = PublishRepository(session)

    published = await contents.count_published_posts(
        workspace_id=workspace_id, start=start, end=now
    )
    inbox_received = await inboxes.count_in_range(
        workspace_id=workspace_id, start=start, end=now
    )
    replies_sent = await inboxes.count_by_status_in_range(
        workspace_id=workspace_id, status=InboxItemStatus.SENT, start=start, end=now
    )
    publish_counts = await publishes.status_counts_for_window(
        workspace_id=workspace_id, start=start, end=now
    )
    publish_failed = publish_counts.get(PublishStatus.FAILED, 0) + publish_counts.get(
        PublishStatus.DEAD_LETTER, 0
    )

    # Việc đang chờ lấy cùng nguồn với hàng đợi, để hai màn không bao giờ nói hai
    # con số khác nhau về cùng một thứ.
    open_items = await inboxes.list_open(workspace_id=workspace_id, limit=QUEUE_LIMIT)
    drafts_pending = (
        await contents.count_items_by_status(workspace_id=workspace_id)
    ).get(ContentStatus.PENDING_APPROVAL, 0)
    # Một lần đọc, hai câu hỏi: kênh nào hỏng, và kênh nào đang mở mà im lặng.
    connections = await ConnectionRepository(session).list_for_workspace(workspace_id)
    broken_connections = sum(
        1 for connection in connections if connection.status is not ConnectionStatus.CONNECTED
    )
    open_failures = len(
        await publishes.list_for_workspace(workspace_id=workspace_id, status=PublishStatus.FAILED)
    ) + len(
        await publishes.list_for_workspace(
            workspace_id=workspace_id, status=PublishStatus.DEAD_LETTER
        )
    )

    # Chỗ trống lịch: gom ngày (theo giờ VN) đã có bài, rồi lấy phần thiếu.
    horizon = now + timedelta(days=brief_policy.GAP_LOOKAHEAD_DAYS + 1)
    scheduled = await contents.list_items_in_range(
        workspace_id=workspace_id, start=now, end=horizon
    )
    scheduled_dates = {
        item.scheduled_at.astimezone(VIETNAM_TZ).date()
        for item in scheduled
        if item.scheduled_at is not None
    }
    today = now.astimezone(VIETNAM_TZ).date()
    gaps = brief_policy.calendar_gaps(scheduled_dates=scheduled_dates, today=today)

    # Kênh im lặng. Chỉ soi kênh workspace **thật sự đăng được**: kênh đã mở
    # (`LIVE_CHANNELS`) và nền tảng còn kết nối. Kênh mất quyền đã là một việc
    # riêng trong hàng đợi, và nhắc "chưa đăng" ở đó là kể lại hậu quả thay vì
    # nguyên nhân. Mốc của kênh chưa từng đăng là ngày nối kênh.
    watched: dict[Channel, date] = {}
    for connection in connections:
        if connection.status is not ConnectionStatus.CONNECTED:
            continue
        connected_since = connection.created_at.astimezone(VIETNAM_TZ).date()
        for channel in PLATFORM_TO_CHANNELS.get(connection.platform, []):
            if channel in channel_capabilities.LIVE_CHANNELS:
                watched[channel] = connected_since
    silent = brief_policy.silent_channels(
        watched=watched,
        last_published={
            channel: published_at.astimezone(VIETNAM_TZ).date()
            for channel, published_at in (
                await contents.last_published_by_channel(workspace_id=workspace_id)
            ).items()
        },
        today=today,
    )

    actions = brief_policy.time_saved(replies_sent=replies_sent, posts_published=published)

    return MorningBrief(
        generated_at=now,
        window_hours=window_hours,
        activity=BriefActivity(
            published=published,
            inbox_received=inbox_received,
            replies_sent=replies_sent,
            publish_failed=publish_failed,
        ),
        attention_total=(
            len(open_items) + drafts_pending + broken_connections + open_failures
        ),
        attention_costly=sum(
            1 for item, _ in open_items if inbox_triage.is_costly(item.category)
        ),
        calendar_gaps=[
            BriefGap(date=day, weekday=brief_policy.weekday_name(day)) for day in gaps
        ],
        silent_channels=[
            BriefSilentChannel(
                channel=item.channel,
                label=channel_capabilities.CHANNEL_LABELS[item.channel],
                days=item.days,
                ever_published=item.ever_published,
            )
            for item in silent
        ],
        time_saved_minutes=brief_policy.total_minutes_saved(actions),
        time_saved_actions=[
            BriefSavedAction(
                action=action.action,
                count=action.count,
                minutes_each=action.minutes_each,
                minutes_total=action.minutes_total,
            )
            for action in actions
        ],
    )
