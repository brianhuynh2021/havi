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

from api.deps import InboxServiceDep, JobQueueDep, SettingsDep, WorkspaceDep
from core.enums import Platform
from core.request_context import get_request_id
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
    job_queue: JobQueueDep,
) -> dict[str, str]:
    """Nhận tin nhắn và bình luận từ Facebook Page — trả 200 ngay sau khi xác thực."""
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
    job_queue.enqueue_webhook_payload(payload=payload, request_id=get_request_id())
    return {"status": "ok"}


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
