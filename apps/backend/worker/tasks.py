"""Các job của worker — khung rỗng, điền khi nối LLM và adapter thật.

Phễu listening (tiết kiệm token): 100% bài → keyword + rule (0 token) → ~5% → model rẻ
chấm điểm ý định → ~1% → LLM soạn trả lời → dừng ở pending_approval.
"""

import asyncio
import logging
from uuid import UUID

from application.services.content_engine import GenerationFailed
from application.services.content_service import ContentJobNotFound, WorkspaceNotFound
from core.request_context import reset_request_id, set_request_id
from worker.celery_app import celery_app

logger = logging.getLogger("havi.worker.tasks")


@celery_app.task(name="havi.content.generate_drafts", bind=True, max_retries=3)
def generate_drafts(self, workspace_id: str, job_id: str, request_id: str | None = None) -> None:  # noqa: ANN001
    """Ingest media → đọc brand profile → 1 lần gọi LLM sinh mọi kênh.

    Trạng thái draft khi sinh xong lấy từ `core.content_state.initial_status(publish_mode)`.

    Không Celery-retry khi `GenerationFailed`: ProviderRouter đã thử lần lượt mọi
    provider được cấu hình rồi mới ném lỗi này, nên retry cùng prompt gần như chỉ
    lặp lại thất bại và tốn thêm tiền. Job đã được đánh `failed` kèm reason để chủ
    tiệm thấy và bấm tạo lại nếu muốn. Celery retry vẫn giữ cho lỗi hạ tầng
    (DB/Redis mất kết nối) — những lỗi đó thoát ra ngoài như exception khác.
    """
    from worker.content_engine_factory import content_engine_scope

    async def _run() -> None:
        ws_id = UUID(workspace_id)
        j_id = UUID(job_id)
        for attempt in range(3):
            try:
                async with content_engine_scope() as engine:
                    await engine.generate_drafts(workspace_id=ws_id, job_id=j_id)
                    return
            except ContentJobNotFound:
                if attempt < 2:
                    await asyncio.sleep(0.3)
                else:
                    raise

    token = set_request_id(request_id) if request_id else None
    try:
        try:
            asyncio.run(_run())
        except (GenerationFailed, ContentJobNotFound, WorkspaceNotFound) as exc:
            logger.warning("Worker skipping job %s (%s)", job_id, type(exc).__name__)
            return
    finally:
        if token is not None:
            reset_request_id(token)


@celery_app.task(name="havi.listening.classify", bind=True)
def classify_listening_item(self, inbox_item_id: str) -> None:  # noqa: ANN001
    """Rule + model nhỏ chấm điểm ý định trước khi động tới LLM xịn."""
    del self, inbox_item_id
    raise NotImplementedError


@celery_app.task(name="havi.reply.draft", bind=True)
def draft_reply(self, inbox_item_id: str) -> None:  # noqa: ANN001
    """Soạn `ai_suggested_reply`. Luôn dừng ở pending_approval — không tự gửi."""
    del self, inbox_item_id
    raise NotImplementedError


@celery_app.task(name="havi.publish.run_due", max_retries=0)
def publish_run_due(limit: int = 20, request_id: str | None = None) -> int:
    """Chạy các publish job đã đến hạn. Trả số job đã nhận trong lượt này.

    Không nhận `content_item_id`: job được nhận bằng `claim_due`
    (`FOR UPDATE SKIP LOCKED`) chứ không bằng tham số của message. Đó là chủ ý —
    nếu id nằm trong message thì Celery giao lại một message (điều nó *được phép*
    làm với `task_acks_late`) là hai worker cùng đăng một bài. Khoá phải ở
    Postgres, không ở hàng đợi.

    Retry cũng không do Celery: `mark_failed` xếp lịch thử lại theo
    `PublishFailureKind` (temporary → backoff 60/300/900s; auth_permission và
    validation_permanent → dead-letter ngay). Thêm `max_retries` của Celery lên
    trên là hai cơ chế retry lệch nhau trên cùng một job.
    """
    from worker.publish_service_factory import publish_service_scope

    async def _run() -> int:
        async with publish_service_scope() as service:
            return len(await service.run_due(limit=limit))

    token = set_request_id(request_id) if request_id else None
    try:
        return asyncio.run(_run())
    finally:
        if token is not None:
            reset_request_id(token)


@celery_app.task(name="havi.video.publish", bind=True, max_retries=0)
def publish_video_post(self, workspace_id: str, post_id: str, request_id: str | None = None) -> None:  # noqa: ANN001
    """Đăng một video đã duyệt lên Facebook Reels rồi xác minh.

    `max_retries=0` là chủ ý và là luật quan trọng nhất của task này. Celery
    retry ở đây nghĩa là gửi lại một video có thể đã lên Trang — chính xác cách
    tạo ra hai Reels giống hệt nhau. Việc thử lại do
    `VideoPublishService` quyết định qua trạng thái `PENDING_RECONCILIATION`,
    và ở đó nó *đối soát* chứ không gửi lại.
    """
    from application.services.video_publish_service import (
        ChannelNotConnected,
        VideoNotReadyForPublish,
    )
    from worker.video_publish_factory import video_publish_scope

    async def _run() -> None:
        async with video_publish_scope() as service:
            outcome = await service.publish(
                workspace_id=UUID(workspace_id), post_id=UUID(post_id)
            )
            logger.info(
                "Video %s sau khi đăng: %s (bài %s)",
                post_id,
                outcome.post.status.value,
                outcome.external_post_id,
            )

    token = set_request_id(request_id) if request_id else None
    try:
        try:
            asyncio.run(_run())
        except (VideoNotReadyForPublish, ChannelNotConnected) as exc:
            logger.warning("Bỏ qua lượt đăng video %s: %s", post_id, exc)
    finally:
        if token is not None:
            reset_request_id(token)


@celery_app.task(name="havi.video.publish_due", max_retries=0)
def publish_due_video_posts(limit: int = 20, request_id: str | None = None) -> int:
    """Gửi những video đã duyệt và đã tới giờ. Trả số clip đã xử trong lượt này.

    Chạy định kỳ, chọn bản ghi bằng truy vấn chứ không nhận `post_id` qua
    message: một message bị Celery giao lại không biến thành hai lượt gửi cùng
    một clip.

    Không `raise` khi một clip hỏng — một Trang mất kết nối không được làm kẹt
    lịch đăng của mọi workspace khác trong cùng lượt quét.
    """
    from application.services.video_publish_service import (
        ChannelNotConnected,
        VideoNotReadyForPublish,
    )
    from worker.video_publish_factory import video_publish_scope

    async def _run() -> int:
        sent = 0
        async with video_publish_scope() as service:
            for post in await service.due_posts(limit=limit):
                try:
                    await service.publish(
                        workspace_id=post.workspace_id, post_id=post.id
                    )
                    sent += 1
                except (VideoNotReadyForPublish, ChannelNotConnected) as exc:
                    logger.warning("Bỏ qua video %s tới giờ: %s", post.id, exc)
                except Exception:
                    logger.exception("Gửi video %s hỏng", post.id)
        return sent

    token = set_request_id(request_id) if request_id else None
    try:
        return asyncio.run(_run())
    finally:
        if token is not None:
            reset_request_id(token)


@celery_app.task(name="havi.video.reconcile", max_retries=0)
def reconcile_video_publishes(limit: int = 20, request_id: str | None = None) -> int:
    """Đối soát các lần gửi đã mất dấu. Trả số lần đã kiểm trong lượt này.

    Chạy định kỳ. Không nhận `job_id` từ message: job được chọn bằng truy vấn
    trong DB, nên một message bị Celery giao lại không biến thành hai lượt đối
    soát cùng một bản ghi.
    """
    from adapters.persistence.video_publish_repository import VideoPublishRepository
    from worker.video_publish_factory import video_publish_scope

    async def _run() -> int:
        checked = 0
        async with video_publish_scope() as service:
            repo: VideoPublishRepository = service._attempts  # noqa: SLF001
            for attempt in await repo.list_needing_reconciliation(limit=limit):
                try:
                    await service.reconcile(
                        workspace_id=attempt.workspace_id, attempt=attempt
                    )
                    checked += 1
                except Exception:
                    logger.exception("Đối soát attempt %s hỏng", attempt.id)
        return checked

    token = set_request_id(request_id) if request_id else None
    try:
        return asyncio.run(_run())
    finally:
        if token is not None:
            reset_request_id(token)


@celery_app.task(name="havi.inbox.process_webhook", bind=True, max_retries=3)
def process_webhook_payload(
    self, payload: dict, request_id: str | None = None
) -> dict[str, int]:  # noqa: ANN001
    """Xử lý webhook payload từ Facebook/Meta đã được xác thực chữ ký ở router.

    TẠI SAO CẦN RETRY Ở ĐÂY:
    Router đã trả HTTP 200 cho Meta ngay khi chữ ký hợp lệ để tránh webhook timeout.
    Meta coi như sự kiện đã được giao thành công và SẼ KHÔNG GỬI LẠI (Meta chỉ redeliver
    khi nhận non-200). Do đó, Celery task này là rào chắn duy nhất bảo vệ tin nhắn của
    khách không bị biến mất vĩnh viễn khi gặp lỗi tạm thời (DB gián đoạn, lỗi mạng).

    1. Mỗi event trong batch được xử lý trong một inbox_service_scope() độc lập, đảm bảo
       một event lỗi không làm rollback các event anh em đã xử lý thành công.
    2. Lỗi dữ liệu/logic của từng event được log exception và ghi nhận vào EventLog với
       field error (để hiển thị được ở GET /analytics/events?error=...).
    3. Lỗi hạ tầng transient (DB/mạng mất kết nối) sẽ kích hoạt self.retry() với
       exponential backoff countdown.
    """
    from sqlalchemy.exc import DatabaseError, DBAPIError, InterfaceError, OperationalError

    from core.enums import Platform
    from core.events import EventLogEntry
    from domain.policies.inbox_triage import iter_inquiries
    from worker.inbox_service_factory import inbox_service_scope

    transient_exceptions = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
        OSError,
        OperationalError,
        DatabaseError,
        InterfaceError,
        DBAPIError,
    )

    async def _run() -> dict[str, int]:
        accepted = 0
        skipped = 0
        failed = 0

        for event in iter_inquiries(payload):
            try:
                async with inbox_service_scope() as (inbox_service, connections, events):
                    connection = await connections.find_by_external_account(
                        platform=Platform.FACEBOOK, external_account_id=event.page_id
                    )
                    if connection is None:
                        # Trang không thuộc workspace nào đang kết nối. Bỏ qua chứ không lỗi:
                        # một app Meta có thể nhận sự kiện của trang đã ngắt kết nối.
                        skipped += 1
                        continue

                    item = await inbox_service.process_inquiry(
                        workspace_id=connection.workspace_id,
                        platform=Platform.FACEBOOK,
                        author_name=event.author_name,
                        content=event.text,
                        item_type=event.item_type,
                        external_message_id=event.message_id,
                        recipient_id=event.sender_id,
                    )
                    await events.record(
                        EventLogEntry(
                            workspace_id=connection.workspace_id,
                            job_kind="inbox.webhook_received",
                            input_summary=f"meta_webhook:page_{event.page_id}",
                            output_summary=f"msg_id:{event.message_id} | psid:{event.sender_id} | item_id:{item.id}",
                        )
                    )
                    accepted += 1
            except transient_exceptions:
                # Lỗi hạ tầng tạm thời (DB/mạng) -> raise để task-level retry xử lý
                raise
            except Exception as exc:
                # Lỗi logic/dữ liệu hỏng ở 1 event -> ghi log, record error event, không làm hỏng event khác
                logger.exception(
                    "meta_webhook.event_failed message_id=%s page_id=%s: %s",
                    getattr(event, "message_id", None),
                    getattr(event, "page_id", None),
                    exc,
                )
                failed += 1
                try:
                    async with inbox_service_scope() as (_, connections, events):
                        conn = await connections.find_by_external_account(
                            platform=Platform.FACEBOOK, external_account_id=event.page_id
                        )
                        if conn is not None:
                            await events.record(
                                EventLogEntry(
                                    workspace_id=conn.workspace_id,
                                    job_kind="inbox.webhook_received",
                                    input_summary=f"meta_webhook:page_{event.page_id}",
                                    output_summary=f"msg_id:{event.message_id} | psid:{event.sender_id}",
                                    error=str(exc)[:500],
                                )
                            )
                except Exception:
                    logger.exception("Failed to record error event for failed inquiry")

        return {"accepted": accepted, "skipped": skipped, "failed": failed}

    token = set_request_id(request_id) if request_id else None
    try:
        try:
            return asyncio.run(_run())
        except transient_exceptions as exc:
            retries = getattr(getattr(self, "request", None), "retries", 0)
            max_retries = getattr(self, "max_retries", 3)
            if retries < max_retries:
                countdown = 2**retries * 2
                logger.warning(
                    "Transient error in process_webhook_payload, retrying (%s/%s) in %ss: %s",
                    retries + 1,
                    max_retries,
                    countdown,
                    exc,
                )
                raise self.retry(exc=exc, countdown=countdown) from exc
            logger.exception("process_webhook_payload exhausted retries: %s", exc)
            raise
    finally:
        if token is not None:
            reset_request_id(token)
