"""/webhooks/* — đường vào của sự kiện từ nền tảng.

Đây là mặt phẳng dữ liệu vào duy nhất của Station 4. Trước khi có nó, bảng
`inbox_items` không có cách nào nhận được tin nhắn thật: `process_inquiry` không
được router nào gọi, nên Unified Inbox chỉ chạy được với dữ liệu seed.

Ba tính chất bắt buộc của mọi endpoint ở đây, vì chúng public và không có JWT:

1. **Xác thực chữ ký trước khi đọc body.** Không có chữ ký hợp lệ thì request
   không phải của nền tảng, và Havi không được tạo dữ liệu từ nó.
2. **Chống trùng theo ID sự kiện.** Meta gửi lại khi không nhận được 200 trong
   ~20 giây. Gửi lại không được sinh thêm tin nhắn khách.
3. **Luôn trả 200 sau khi đã nhận.** Lỗi xử lý một item không được làm nền tảng
   retry vô hạn cả lô; lỗi đi vào `event_log`, không đi vào status code.
"""

import hashlib
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.db import DbSessionDep
from adapters.persistence.event_log_repository import EventLogRepository
from api.deps import InboxServiceDep, SettingsDep, WorkspaceDep
from core.enums import InboxItemType, Platform
from core.events import EventLogEntry
from core.schemas import HaviModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class SimulatedInquiry(HaviModel):
    """Payload của endpoint mô phỏng ở local."""

    content: str
    author_name: str = "Khách thử nghiệm"
    platform: Platform = Platform.FACEBOOK
    external_message_id: str | None = None


def _signature_matches(*, app_secret: str, raw_body: bytes, header: str | None) -> bool:
    """So khớp `X-Hub-Signature-256` theo cách Meta quy định.

    `compare_digest` chứ không `==`: so sánh chuỗi thường thoát sớm ở byte đầu
    khác nhau, và thời gian thoát đó đủ để dò dần chữ ký đúng.
    """
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


@router.get("/meta", include_in_schema=False)
async def verify_meta_webhook(request: Request, settings: SettingsDep) -> Response:
    """Bắt tay xác minh khi khai webhook trong Meta App Dashboard.

    Meta gọi một lần với `hub.verify_token`; khớp thì phải trả lại đúng
    `hub.challenge` dưới dạng text thuần.
    """
    params = request.query_params
    verify_token = settings.meta_webhook_verify_token
    if not verify_token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook chưa cấu hình")

    if params.get("hub.mode") != "subscribe" or not hmac.compare_digest(
        params.get("hub.verify_token", ""), verify_token
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Verify token không khớp")

    return Response(content=params.get("hub.challenge", ""), media_type="text/plain")


@router.post("/meta", include_in_schema=False)
async def receive_meta_webhook(
    request: Request,
    settings: SettingsDep,
    session: DbSessionDep,
    inbox_service: InboxServiceDep,
) -> dict[str, int]:
    """Nhận tin nhắn và bình luận từ Facebook Page."""
    app_secret = settings.facebook_client_secret
    if not app_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook chưa cấu hình")

    raw_body = await request.body()
    if not _signature_matches(
        app_secret=app_secret,
        raw_body=raw_body,
        header=request.headers.get("X-Hub-Signature-256"),
    ):
        # Không log body: request chưa xác thực có thể chứa bất kỳ thứ gì và
        # ghi thẳng vào log là biến log thành nơi chứa dữ liệu người lạ.
        logger.warning("meta_webhook.invalid_signature")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chữ ký không hợp lệ")

    payload = await request.json()
    connections = ConnectionRepository(session)
    events = EventLogRepository(session)
    accepted = 0
    skipped = 0

    for event in _iter_inquiries(payload):
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

    return {"accepted": accepted, "skipped": skipped}


@router.post("/dev/simulate", include_in_schema=False)
async def simulate_inbound(
    payload: SimulatedInquiry,
    workspace_id: WorkspaceDep,
    settings: SettingsDep,
    inbox_service: InboxServiceDep,
) -> dict[str, str]:
    """Bơm một tin nhắn giả vào inbox của workspace đang đăng nhập — CHỈ Ở LOCAL.

    Cùng lý do với mock LLM và fake publisher: xây UI và báo cáo cần dữ liệu để
    nhìn, nhưng dữ liệu giả lọt lên staging/production là chủ tiệm thấy khách
    không có thật. Chặn bằng `HAVI_ENV` chứ không bằng flag riêng, để nó nằm
    dưới đúng cái công tắc mà `docs/handoff/DEPLOYMENT.md` đã kiểm.

    Đi qua đúng `process_inquiry` mà webhook thật dùng, nên FAQ matching, chống
    trùng và event log đều được diễn tập thật.
    """
    if settings.env != "local":
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Endpoint này chỉ tồn tại ở môi trường local"
        )

    item = await inbox_service.process_inquiry(
        workspace_id=workspace_id,
        platform=payload.platform,
        author_name=payload.author_name,
        content=payload.content,
        external_message_id=payload.external_message_id,
    )
    return {"id": str(item.id), "status": item.status.value}


class _Inquiry:
    """Một sự kiện đã bóc tách, chuẩn hoá khỏi khác biệt giữa các loại webhook."""

    __slots__ = (
        "page_id",
        "message_id",
        "author_name",
        "text",
        "sender_id",
        "item_type",
    )

    def __init__(
        self,
        *,
        page_id: str,
        message_id: str,
        author_name: str,
        text: str,
        sender_id: str | None = None,
        item_type: InboxItemType = InboxItemType.MESSAGE,
    ):
        self.page_id = page_id
        self.message_id = message_id
        self.author_name = author_name
        self.text = text
        self.sender_id = sender_id
        self.item_type = item_type


def _iter_inquiries(payload: dict):
    """Bóc `messaging` (tin nhắn) và `changes` (bình luận) ra cùng một hình dạng.

    Hàm thuần, không I/O — chỗ dễ sai nhất của webhook là hình dạng payload, nên
    tách ra để test được mà không cần dựng HTTP hay DB.
    """
    for entry in payload.get("entry", []) or []:
        page_id = str(entry.get("id") or "")
        if not page_id:
            continue

        for messaging in entry.get("messaging", []) or []:
            message = messaging.get("message") or {}
            text = (message.get("text") or "").strip()
            message_id = message.get("mid")
            sender_id = (messaging.get("sender") or {}).get("id")
            if not text or not message_id:
                continue
            # Bỏ echo: tin do chính Page gửi cũng quay lại qua webhook, nhận vào
            # thì inbox đầy những câu của chính chủ tiệm.
            if messaging.get("message", {}).get("is_echo"):
                continue
            yield _Inquiry(
                page_id=page_id,
                message_id=str(message_id),
                author_name=f"Khách {str(sender_id)[-4:]}" if sender_id else "Khách",
                text=text,
                sender_id=str(sender_id) if sender_id else None,
            )

        for change in entry.get("changes", []) or []:
            if change.get("field") != "feed":
                continue
            value = change.get("value") or {}
            if value.get("item") != "comment" or value.get("verb") != "add":
                continue
            text = (value.get("message") or "").strip()
            comment_id = value.get("comment_id")
            if not text or not comment_id:
                continue
            author = (value.get("from") or {}).get("name") or "Khách"
            from_id = (value.get("from") or {}).get("id")
            yield _Inquiry(
                page_id=page_id,
                message_id=str(comment_id),
                author_name=author,
                text=text,
                sender_id=str(from_id) if from_id else None,
                item_type=InboxItemType.COMMENT,
            )
