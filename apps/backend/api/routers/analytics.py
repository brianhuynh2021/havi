"""/analytics — báo cáo trạng thái xuất bản và hội thoại từ dữ liệu Havi."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.db import DbSessionDep
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.inbox_repository import InboxRepository
from adapters.persistence.publish_repository import PublishRepository
from api.deps import AuditViewerWorkspaceDep, WorkspaceDep
from core.enums import ConnectionStatus, ContentStatus, InboxItemStatus, PublishStatus
from core.schemas import (
    AnalyticsSummary,
    AnalyticsTimeseries,
    ChannelAttribution,
    DashboardContentSummary,
    EventLogRecord,
    FailedPostRecord,
    OperationsMetrics,
    OperationsPublishMetric,
    Page,
)
from domain.models.content import ContentItem
from domain.models.publish import PublishJob
from domain.policies.scheduling import VIETNAM_TZ

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _date_range(start: date, end: date) -> tuple[datetime, datetime]:
    if end < start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "`end` phải sau `start`")
    range_start = datetime.combine(start, time.min, tzinfo=VIETNAM_TZ).astimezone(UTC)
    range_end = datetime.combine(end + timedelta(days=1), time.min, tzinfo=VIETNAM_TZ).astimezone(
        UTC
    )
    return range_start, range_end


@router.get("/dashboard", response_model=DashboardContentSummary)
async def dashboard(workspace_id: WorkspaceDep, session: DbSessionDep) -> DashboardContentSummary:
    """Số liệu thật tối thiểu cho tab Tổng quan."""
    counts = await ContentRepository(session).count_items_by_status(workspace_id=workspace_id)
    
    connections = await ConnectionRepository(session).list_for_workspace(workspace_id)
    total_connections = len(connections)
    broken_connections = sum(1 for c in connections if c.status != ConnectionStatus.CONNECTED)

    unhandled_inbox = await InboxRepository(session).count_by_statuses(
        workspace_id=workspace_id,
        statuses=[InboxItemStatus.NEW, InboxItemStatus.DRAFTED]
    )

    return DashboardContentSummary(
        drafts=counts.get(ContentStatus.DRAFT, 0),
        pending_approval=counts.get(ContentStatus.PENDING_APPROVAL, 0),
        scheduled=counts.get(ContentStatus.SCHEDULED, 0),
        published=counts.get(ContentStatus.PUBLISHED, 0),
        failed=counts.get(ContentStatus.FAILED, 0) + counts.get(ContentStatus.DEAD_LETTER, 0),
        broken_connections=broken_connections,
        total_connections=total_connections,
        unhandled_inbox=unhandled_inbox,
    )


@router.get("/events", response_model=Page[EventLogRecord])
async def events(
    # Lịch sử hoạt động lộ ra ai làm gì trong cả workspace. Người soạn và trực
    # hội thoại không cần thấy — và không nên thấy.
    workspace_id: AuditViewerWorkspaceDep,
    session: DbSessionDep,
    job_id: UUID | None = None,
    request_id: str | None = Query(default=None, max_length=80),
    job_kind: str | None = Query(default=None, max_length=80),
    provider: str | None = Query(default=None, max_length=80),
    error_only: bool = False,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[EventLogRecord]:
    """Event log đã scope theo workspace để support debug.

    Chưa có `request_id`: code hiện tại chưa gắn request id vào log context hoặc
    bảng `event_log`, nên endpoint này chỉ expose các khoá thật đang được lưu.
    """
    rows, total = await EventLogRepository(session).list_for_workspace(
        workspace_id=workspace_id,
        job_id=job_id,
        request_id=request_id,
        job_kind=job_kind,
        provider=provider,
        error_only=error_only,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[EventLogRecord.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/operations", response_model=OperationsMetrics)
async def operations(
    workspace_id: WorkspaceDep, session: DbSessionDep, start: date, end: date
) -> OperationsMetrics:
    """Dashboard nội bộ tối thiểu: latency, lỗi, token và publish health."""
    range_start, range_end = _date_range(start, end)
    event_metrics = await EventLogRepository(session).operations_metrics(
        workspace_id=workspace_id, start=range_start, end=range_end
    )
    publish_counts = await PublishRepository(session).status_counts_for_window(
        workspace_id=workspace_id, start=range_start, end=range_end
    )
    publish_total = sum(publish_counts.values())
    publish_succeeded = publish_counts.get(PublishStatus.SUCCEEDED, 0)
    publish_dead_letter = publish_counts.get(PublishStatus.DEAD_LETTER, 0)
    return OperationsMetrics(
        window_start=range_start,
        window_end=range_end,
        publish=OperationsPublishMetric(
            total=publish_total,
            succeeded=publish_succeeded,
            dead_letter=publish_dead_letter,
            success_rate=round(publish_succeeded / publish_total, 4) if publish_total else 0,
            dead_letter_rate=round(publish_dead_letter / publish_total, 4) if publish_total else 0,
        ),
        **event_metrics,
    )


def _percent_change(current: float, previous: float) -> float:
    """Phần trăm thay đổi so kỳ trước.

    Kỳ trước bằng 0 thì không có phần trăm nào đúng cả (chia cho 0), nên trả 0 và
    để UI hiển thị con số tuyệt đối — bịa ra "+100%" từ 0→1 là phóng đại.
    """
    if previous <= 0:
        return 0.0
    return round((current - previous) / previous * 100, 1)


async def _outcomes_for(
    session, *, workspace_id: UUID, start: datetime, end: datetime
) -> dict[str, float]:
    inbox = InboxRepository(session)
    inbox_items = await inbox.count_in_range(
        workspace_id=workspace_id, start=start, end=end
    )
    replies_sent = await inbox.count_by_status_in_range(
        workspace_id=workspace_id,
        status=InboxItemStatus.SENT,
        start=start,
        end=end,
    )
    published = await ContentRepository(session).count_published_posts(
        workspace_id=workspace_id, start=start, end=end
    )
    publish_counts = await PublishRepository(session).status_counts_for_window(
        workspace_id=workspace_id, start=start, end=end
    )
    return {
        "published_posts": published,
        "inbox_items": inbox_items,
        "replies_sent": replies_sent,
        "failed_posts": publish_counts.get(PublishStatus.DEAD_LETTER, 0)
        + publish_counts.get(PublishStatus.FAILED, 0),
    }


@router.get("/summary", response_model=AnalyticsSummary)
async def summary(
    workspace_id: WorkspaceDep, session: DbSessionDep, start: date, end: date
) -> AnalyticsSummary:
    """Các số liệu vận hành trong kỳ, kèm thay đổi so với kỳ trước."""
    range_start, range_end = _date_range(start, end)
    span = range_end - range_start
    current = await _outcomes_for(
        session, workspace_id=workspace_id, start=range_start, end=range_end
    )
    previous = await _outcomes_for(
        session,
        workspace_id=workspace_id,
        start=range_start - span,
        end=range_start,
    )

    return AnalyticsSummary(
        published_posts=int(current["published_posts"]),
        inbox_items=int(current["inbox_items"]),
        replies_sent=int(current["replies_sent"]),
        failed_posts=int(current["failed_posts"]),
        change_vs_previous_period={
            key: _percent_change(current[key], previous[key]) for key in current
        },
    )


@router.get("/attribution", response_model=list[ChannelAttribution])
async def attribution(
    workspace_id: WorkspaceDep, session: DbSessionDep, start: date, end: date
) -> list[ChannelAttribution]:
    """Phân bổ bài đã đăng theo kênh."""
    range_start, range_end = _date_range(start, end)
    counts = await ContentRepository(session).count_published_by_channel(
        workspace_id=workspace_id, start=range_start, end=range_end
    )
    total = sum(counts.values())
    return [
        ChannelAttribution(
            channel=channel,
            posts=count,
            share=round(count / total, 4) if total else 0,
            note="Tính theo bài đã được nền tảng xác nhận đăng thành công.",
        )
        for channel, count in sorted(counts.items(), key=lambda item: item[0].value)
    ]


def _period_start(value: datetime, *, granularity: str) -> datetime:
    local = value.astimezone(VIETNAM_TZ)
    if granularity == "month":
        return datetime(local.year, local.month, 1, tzinfo=VIETNAM_TZ)
    monday = local.date() - timedelta(days=local.weekday())
    return datetime.combine(monday, time.min, tzinfo=VIETNAM_TZ)


def _period_label(value: datetime, *, granularity: str) -> str:
    if granularity == "month":
        return value.strftime("%Y-%m")
    year, week, _ = value.isocalendar()
    return f"{year}-W{week:02d}"


def _month_start_offset(value: datetime, offset: int) -> datetime:
    month_index = value.year * 12 + (value.month - 1) - offset
    year = month_index // 12
    month = month_index % 12 + 1
    return datetime(year, month, 1, tzinfo=VIETNAM_TZ)


@router.get("/timeseries", response_model=AnalyticsTimeseries)
async def timeseries(
    workspace_id: WorkspaceDep,
    session: DbSessionDep,
    metric: str,
    granularity: str = Query(default="week", pattern="^(week|month)$"),
) -> AnalyticsTimeseries:
    """Bar chart 4 tuần."""
    if metric != "published_posts":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Metric hiện hỗ trợ: published_posts",
        )

    now = datetime.now(VIETNAM_TZ)
    current = _period_start(now, granularity=granularity)
    if granularity == "month":
        starts = [_month_start_offset(current, offset) for offset in reversed(range(4))]
    else:
        starts = [current - timedelta(days=7 * offset) for offset in reversed(range(4))]
    points = []
    repository = ContentRepository(session)
    for period in starts:
        if granularity == "month":
            next_month = period.month + 1
            next_year = period.year
            if next_month == 13:
                next_month = 1
                next_year += 1
            end = datetime(next_year, next_month, 1, tzinfo=VIETNAM_TZ)
        else:
            end = period + timedelta(days=7)
        count = await repository.count_published_posts(
            workspace_id=workspace_id,
            start=period.astimezone(UTC),
            end=end.astimezone(UTC),
        )
        points.append({"period": _period_label(period, granularity=granularity), "value": count})
    return AnalyticsTimeseries(metric=metric, points=points)


@router.get("/failed-posts", response_model=list[FailedPostRecord])
async def failed_posts(
    workspace_id: WorkspaceDep, session: DbSessionDep, start: date, end: date
) -> list[FailedPostRecord]:
    """Danh sách các bài đăng thất bại trong kỳ, kèm lý do."""
    range_start, range_end = _date_range(start, end)

    result = await session.execute(
        select(ContentItem, PublishJob)
        .join(PublishJob, PublishJob.content_item_id == ContentItem.id)
        .where(
            ContentItem.workspace_id == workspace_id,
            PublishJob.updated_at >= range_start,
            PublishJob.updated_at < range_end,
            PublishJob.status.in_([PublishStatus.FAILED, PublishStatus.DEAD_LETTER])
        )
        .order_by(PublishJob.updated_at.desc())
        .limit(20)
    )
    
    records = []
    for item, job in result.all():
        records.append(
            FailedPostRecord(
                id=item.id,
                channel=item.channel,
                caption=item.text,
                scheduled_at=item.scheduled_at or job.scheduled_at,
                failure_kind=job.failure_kind,
                failure_detail=job.failure_detail,
            )
        )
    return records
