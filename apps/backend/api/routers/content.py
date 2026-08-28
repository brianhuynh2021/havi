"""/content — Content Engine + approval queue.

Đây là nơi triết lý Havi được cưỡng chế: mặc định không có bài nào lên mạng khi chủ
chưa duyệt. Backend ghi `approved_by` / `approved_at` + audit log dù UI duyệt optimistic.
Publish job phải có idempotency key (unique constraint + row lock) để một bài không bị
đăng đúp khi user bấm 2 lần hoặc 2 worker cùng nhận job.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.db import DbSessionDep
from adapters.persistence.media_repository import MediaRepository
from api.deps import (
    ApprovalServiceDep,
    ApproverWorkspaceDep,
    AuthDep,
    ContentServiceDep,
    ObjectStorageDep,
    PublishServiceDep,
    WorkspaceDep,
)
from api.errors import transition_conflict
from api.rate_limit import limit_by_workspace
from application.services.approval_service import ContentItemNotFound, NotReschedulable
from application.services.content_service import (
    ContentJobNotFound,
    MediaNotFound,
    SubscriptionExpired,
    WorkspaceNotFound,
)
from application.services.publish_service import (
    CHANNEL_TO_PLATFORM,
    AlreadyRunning,
    NotRetryable,
    PublishJobNotFound,
)
from core.content_state import InvalidTransitionError
from core.enums import (
    Channel,
    ConnectionStatus,
    ContentKind,
    ContentStatus,
    PublishStatus,
)
from core.schemas import (
    ApproveRequest,
    BulkApproveFailure,
    BulkApproveRequest,
    BulkApproveResult,
    BulkDismissRequest,
    BulkDismissResult,
    ChannelOption,
    ContentItem,
    ContentItemUpdate,
    ContentItemVersion,
    ContentJob,
    ContentJobCreate,
    ContentPreview,
    OwnContentItemCreate,
    Page,
    PublishJob,
    RejectContentItemRequest,
    TokenQuota,
)
from domain.policies import channel_capabilities, rate_limits
from domain.policies.facebook_render import (
    FACEBOOK_TRUNCATE_CHARS,
    facebook_render_warnings,
)
from domain.policies.quota import QuotaExceeded

logger = logging.getLogger("havi.content")

router = APIRouter(prefix="/content", tags=["content"])


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy content item")


def _job_to_schema(job, item_ids: list[UUID]) -> ContentJob:
    return ContentJob(
        id=job.id,
        workspace_id=job.workspace_id,
        status=job.status,
        raw_inputs=job.raw_inputs,
        content_item_ids=item_ids,
        created_at=job.created_at,
    )


@router.post(
    "/jobs",
    response_model=ContentJob,
    status_code=status.HTTP_202_ACCEPTED,
    # Ba lớp chặn khác nhau, không trùng nhau: `Idempotency-Key` chặn bấm hai lần,
    # rate limit chặn *nhịp* (đốt hết quota tháng trong vài phút), quota chặn
    # *tổng* tháng. Thiếu lớp giữa thì một script lỗi vẫn đúng quota mà cháy ngân
    # sách trong buổi sáng.
    dependencies=[limit_by_workspace("content_job", rate_limits.CONTENT_JOB)],
)
async def create_content_job(
    payload: ContentJobCreate,
    workspace_id: WorkspaceDep,
    content_service: ContentServiceDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ContentJob:
    """Nút "Để Havi viết cho chị".

    Đẩy 1 job vào hàng đợi; worker gọi LLM đúng 1 lần và sinh nhiều bản theo kênh.
    API trả ngay `queued`, frontend poll `GET /content/jobs/{id}` cho tới `drafts_ready`.

    Gửi header `Idempotency-Key` để bấm hai lần không tốn hai lần tiền LLM — cùng
    key trong cùng workspace luôn trả về job đầu tiên và không enqueue lần nữa.
    """
    # Cưỡng chế luật nền tảng ở backend, không chỉ ẩn ô tick ở frontend: một client
    # cũ hay một lần gọi API trực tiếp vẫn gửi được `channel=tiktok` cho bài chữ, và
    # lỗi lúc đó chỉ lộ ra ở bước đăng — sau khi đã tốn tiền LLM sinh nháp.
    #
    # `/content/jobs` luôn là bài chữ; video đi qua `/video/posts`.
    for channel in payload.target_channels or []:
        reason = channel_capabilities.reject_reason(
            channel=channel, kind=ContentKind.POST
        )
        if reason is not None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, reason)

    try:
        raw_inputs_data = [item.model_dump(mode="json") for item in payload.raw_inputs]
        if payload.target_channels:
            raw_inputs_data.append(
                {
                    "kind": "text",
                    "text": "",
                    "meta": "channels_filter",
                    "target_channels": [c.value for c in payload.target_channels],
                }
            )
        created = await content_service.create_job(
            workspace_id=workspace_id,
            raw_inputs=raw_inputs_data,
            idempotency_key=idempotency_key,
        )
    except SubscriptionExpired as exc:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            str(exc),
        ) from exc
    except QuotaExceeded as exc:
        # 429 chứ không 402/403: đây là "vượt mức trong khoảng thời gian này", và
        # nó tự hết khi sang tháng — cùng nghĩa với rate limit. 402 hàm ý phải trả
        # tiền ngay mới dùng được, không đúng với gói tính theo tháng.
        # `Retry-After` tính bằng giây theo chuẩn HTTP để client biết chờ tới khi nào.
        retry_after = max(1, int((exc.resets_at - datetime.now(UTC)).total_seconds()))
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            str(exc),
            headers={"Retry-After": str(retry_after)},
        ) from exc

    item_ids = [i.id for i in await content_service.list_items_for_job(created.job.id)]
    return _job_to_schema(created.job, item_ids)


@router.get("/quota", response_model=TokenQuota)
async def get_quota(workspace_id: WorkspaceDep, content_service: ContentServiceDep) -> TokenQuota:
    """Token đã dùng / trần tháng này.

    Frontend đọc để cảnh báo *trước* khi chủ tiệm bị chặn giữa lúc đang cần đăng
    bài. Đặt trước `/{content_id}` vì FastAPI khớp route theo thứ tự khai báo —
    nằm sau thì "quota" bị đọc như một UUID và trả 422.
    """
    status_ = await content_service.quota_status(workspace_id=workspace_id)
    return TokenQuota(
        used=status_.used,
        limit=status_.limit,
        remaining=status_.remaining,
        near_limit=status_.near_limit,
        exceeded=status_.exceeded,
        resets_at=status_.resets_at,
    )


@router.get("/jobs/{job_id}", response_model=ContentJob)
async def get_content_job(
    job_id: UUID, workspace_id: WorkspaceDep, content_service: ContentServiceDep
) -> ContentJob:
    try:
        job = await content_service.get_job(workspace_id=workspace_id, job_id=job_id)
    except ContentJobNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy content job") from exc
    item_ids = [i.id for i in await content_service.list_items_for_job(job.id)]
    return _job_to_schema(job, item_ids)


@router.get("", response_model=Page[ContentItem])
async def list_content(
    workspace_id: WorkspaceDep,
    content_service: ContentServiceDep,
    status: ContentStatus | None = None,
    channel: Channel | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Page[ContentItem]:
    """`status=pending_approval` chính là màn Hàng chờ duyệt."""
    items, total = await content_service.list_items(
        workspace_id=workspace_id,
        status=status,
        channel=channel,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[ContentItem.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/publish-jobs", response_model=list[PublishJob])
async def list_publish_jobs(
    workspace_id: WorkspaceDep,
    publishes: PublishServiceDep,
    status: PublishStatus | None = None,
) -> list[PublishJob]:
    """Lượt đăng của tiệm này. `status=dead_letter` là danh sách bài cần chị xử lý.

    Đặt trước `/{content_id}` trong file: FastAPI khớp route theo thứ tự khai
    báo, nên nếu nằm sau thì "publish-jobs" bị đọc như một UUID và trả 422.
    """
    jobs = await publishes.list_jobs(workspace_id=workspace_id, status=status)
    return [PublishJob.model_validate(job) for job in jobs]


@router.post("/publish-jobs/{job_id}/retry", response_model=PublishJob)
async def retry_publish_job(
    job_id: UUID, workspace_id: WorkspaceDep, publishes: PublishServiceDep
) -> PublishJob:
    """Nút "Thử lại" cho bài đã dừng hẳn sau nhiều lần lỗi (`dead_letter`).

    Chạy ngay và trả kết quả thật — người vừa bấm nút cần biết lần này được hay
    không, chứ không phải một `202 Accepted` rồi tự đi tìm.

    409 khi job không ở `dead_letter`: bài đang chờ scheduler chạy thì bấm thêm
    chỉ tạo cơ hội hai lượt chạy song song, và bài đã đăng thành công thì chạy
    lại là đăng trùng — đúng thứ cả tầng idempotency dựng ra để chặn.
    """
    try:
        job = await publishes.retry_dead_letter(workspace_id=workspace_id, job_id=job_id)
    except PublishJobNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy lượt đăng này") from exc
    except NotRetryable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except AlreadyRunning as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return PublishJob.model_validate(job)


@router.post("/items", response_model=ContentItem, status_code=status.HTTP_201_CREATED)
async def create_own_content_item(
    payload: OwnContentItemCreate,
    workspace_id: WorkspaceDep,
    content_service: ContentServiceDep,
) -> ContentItem:
    """Nút "Tôi tự viết" — đưa bài đã hoàn chỉnh vào hàng chờ, không gọi LLM.

    Khác `/content/jobs` ở chỗ không có model nào chạm vào chữ của người dùng, nên
    trả 201 ngay chứ không 202: không có gì để chờ.

    Trạng thái đầu tiên vẫn theo `publish_mode` của workspace — bài tự viết không
    phải cửa sau để lách bước duyệt.

    Phải khai báo **trước** `/{content_id}`: FastAPI khớp route theo thứ tự, nằm
    sau thì "items" bị đọc như một UUID và trả 422.
    """
    reason = channel_capabilities.reject_reason(
        channel=payload.channel, kind=ContentKind(payload.kind)
    )
    if reason is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, reason)
    try:
        item = await content_service.create_own_item(
            workspace_id=workspace_id,
            text=payload.text,
            channel=payload.channel,
            kind=payload.kind,
            media_id=payload.media_id,
        )
    except MediaNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except WorkspaceNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy workspace") from exc
    return ContentItem.model_validate(item)


@router.post("/preview", response_model=ContentPreview)
async def preview_content(
    payload: OwnContentItemCreate,
    workspace_id: WorkspaceDep,
    session: DbSessionDep,
    storage: ObjectStorageDep,
) -> ContentPreview:
    """Bài sẽ trông thế nào trên Trang — trước khi nó nằm trên tường khách.

    Không ghi gì vào DB: đây là câu hỏi "nếu đăng thì ra sao", không phải một bản
    nháp. Người dùng gõ và xem lại nhiều lần, mỗi lần tạo một hàng rác thì hàng
    chờ duyệt đầy những thứ chưa ai định đăng.

    Trả `truncate_at` thay vì tự cắt chuỗi: giao diện cần cả bài để vẽ được nút
    "Xem thêm" mở ra, còn cắt ở đây thì phần sau không còn để mở.
    """
    media_url: str | None = None
    if payload.media_id is not None:
        asset = await MediaRepository(session).get(
            workspace_id=workspace_id, asset_id=payload.media_id
        )
        if asset is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Không tìm thấy ảnh {payload.media_id}"
            )
        media_url = storage.public_url(asset.object_key)

    warnings = facebook_render_warnings(payload.text)
    return ContentPreview(
        text=payload.text,
        media_url=media_url,
        char_count=len(payload.text),
        truncate_at=(
            FACEBOOK_TRUNCATE_CHARS if len(payload.text) > FACEBOOK_TRUNCATE_CHARS else None
        ),
        warnings=[
            {"code": w.code, "message": w.message, "at_char": w.at_char} for w in warnings
        ],
    )


@router.get("/channels", response_model=list[ChannelOption])
async def list_channel_options(
    workspace_id: WorkspaceDep, session: DbSessionDep
) -> list[ChannelOption]:
    """Kênh chọn được khi soạn bài, kèm loại nội dung mỗi kênh nhận.

    Trả **mọi kênh đang chạy**, không lọc theo `kind`: frontend lọc tại chỗ khi
    người dùng đổi loại nội dung, nên đổi tab không phải chờ mạng.

    Kênh chưa nối vẫn có trong danh sách với `connected: false` — ẩn đi thì người
    dùng không biết là Havi hỗ trợ kênh đó và không biết phải đi nối.

    Phải khai báo **trước** `/{content_id}`: FastAPI khớp route theo thứ tự, nên
    nằm sau thì "channels" bị đọc như một UUID và trả 422.
    """
    connected = {
        connection.platform
        for connection in await ConnectionRepository(session).list_for_workspace(workspace_id)
        if connection.status is ConnectionStatus.CONNECTED
    }

    options: list[ChannelOption] = []
    for channel in Channel:
        if channel not in channel_capabilities.LIVE_CHANNELS:
            continue
        kinds = sorted(channel_capabilities.CHANNEL_ACCEPTS[channel], key=lambda k: k.value)
        options.append(
            ChannelOption(
                channel=channel,
                label=channel_capabilities.CHANNEL_LABELS[channel],
                kinds=kinds,
                connected=CHANNEL_TO_PLATFORM.get(channel) in connected,
            )
        )
    return options


@router.get("/{content_id}", response_model=ContentItem)
async def get_content(
    content_id: UUID, workspace_id: WorkspaceDep, content_service: ContentServiceDep
) -> ContentItem:
    try:
        item = await content_service.get_item(workspace_id=workspace_id, item_id=content_id)
    except ContentJobNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy content item") from exc
    return ContentItem.model_validate(item)


@router.patch("/{content_id}", response_model=ContentItem)
async def update_content(
    content_id: UUID,
    payload: ContentItemUpdate,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
) -> ContentItem:
    """Sửa text tạo `content_item_version` mới, không ghi đè bản cũ.

    Field bỏ trống nghĩa là không đổi. Bài đang `publishing`/`published` trả 409:
    sửa lúc đó sẽ làm bản trên Facebook khác bản trong DB.
    """
    try:
        item = await approvals.update_item(
            workspace_id=workspace_id,
            item_id=content_id,
            user_id=auth.user_id,
            text=payload.text,
            media_note=payload.media_note,
            media_url=payload.media_url,
            scheduled_at=payload.scheduled_at,
        )
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    except NotReschedulable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return ContentItem.model_validate(item)


@router.get("/{content_id}/versions", response_model=list[ContentItemVersion])
async def list_versions(
    content_id: UUID, workspace_id: WorkspaceDep, approvals: ApprovalServiceDep
) -> list[ContentItemVersion]:
    try:
        versions = await approvals.list_versions(workspace_id=workspace_id, item_id=content_id)
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    return [ContentItemVersion.model_validate(v) for v in versions]


@router.post("/approve-all", response_model=BulkApproveResult)
async def approve_all(
    payload: BulkApproveRequest,
    auth: AuthDep,
    # Duyệt là hành động đưa nội dung LÊN KÊNH. Người soạn không tự duyệt bài
    # mình viết — đó là toàn bộ lý do quy trình soạn → duyệt tồn tại.
    workspace_id: ApproverWorkspaceDep,
    approvals: ApprovalServiceDep,
) -> BulkApproveResult:
    """Duyệt cả loạt: `publish_now=true` đăng ngay, `false` thì rải ra nhiều ngày."""
    outcome = await approvals.approve_many(
        workspace_id=workspace_id,
        item_ids=payload.content_item_ids,
        user_id=auth.user_id,
        publish_now=payload.publish_now,
        posts_per_day=payload.posts_per_day,
    )
    try:
        from core.request_context import get_request_id
        from scheduler.tasks import dispatch_due_posts

        dispatch_due_posts.delay(request_id=get_request_id())
    except Exception as exc:
        logger.warning("Failed to trigger dispatch_due_posts: %s", exc)
    return BulkApproveResult(
        approved=outcome.approved,
        rejected=[
            BulkApproveFailure(content_item_id=item_id, reason=reason)
            for item_id, reason in outcome.failures
        ],
    )


@router.post("/dismiss-all", response_model=BulkDismissResult)
async def dismiss_all(
    payload: BulkDismissRequest,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
) -> BulkDismissResult:
    """Nút "Xoá tất cả bản nháp" — chuyển hàng loạt item sang DISMISSED."""
    dismissed = await approvals.dismiss_many(
        workspace_id=workspace_id,
        item_ids=payload.content_item_ids,
        user_id=auth.user_id,
    )
    return BulkDismissResult(dismissed=dismissed)


@router.post("/{content_id}/approve", response_model=ContentItem)
async def approve_content(
    content_id: UUID,
    payload: ApproveRequest,
    auth: AuthDep,
    workspace_id: ApproverWorkspaceDep,
    approvals: ApprovalServiceDep,
) -> ContentItem:
    """Duyệt lẻ 1 bài: pending_approval → approved → scheduled.

    Bỏ trống `scheduled_at` thì Havi chọn khung giờ vàng gần nhất theo giờ VN.
    Trả 409 nếu trạng thái hiện tại không cho phép (xem core.content_state).
    """
    try:
        item = await approvals.approve(
            workspace_id=workspace_id,
            item_id=content_id,
            user_id=auth.user_id,
            scheduled_at=payload.scheduled_at,
        )
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    except InvalidTransitionError as exc:
        raise transition_conflict(exc) from exc
    try:
        from core.request_context import get_request_id
        from scheduler.tasks import dispatch_due_posts

        dispatch_due_posts.delay(request_id=get_request_id())
    except Exception as exc:
        logger.warning("Failed to trigger dispatch_due_posts: %s", exc)
    return ContentItem.model_validate(item)


@router.post("/{content_id}/reject", response_model=ContentItem)
async def reject_content(
    content_id: UUID,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
    payload: RejectContentItemRequest | None = None,
) -> ContentItem:
    """Hoãn bài về bản nháp: pending_approval/scheduled → draft."""
    try:
        item = await approvals.reject(
            workspace_id=workspace_id,
            item_id=content_id,
            user_id=auth.user_id,
            reason=payload.reason if payload else None,
        )
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    except InvalidTransitionError as exc:
        raise transition_conflict(exc) from exc
    return ContentItem.model_validate(item)


@router.post("/{content_id}/dismiss", response_model=ContentItem)
@router.delete("/{content_id}", response_model=ContentItem)
async def dismiss_content(
    content_id: UUID,
    auth: AuthDep,
    workspace_id: WorkspaceDep,
    approvals: ApprovalServiceDep,
) -> ContentItem:
    """Xoá bỏ bài nháp vĩnh viễn: PENDING_APPROVAL/DRAFT/SCHEDULED → DISMISSED."""
    try:
        item = await approvals.dismiss(
            workspace_id=workspace_id, item_id=content_id, user_id=auth.user_id
        )
    except ContentItemNotFound as exc:
        raise _not_found() from exc
    except InvalidTransitionError as exc:
        raise transition_conflict(exc) from exc
    return ContentItem.model_validate(item)
