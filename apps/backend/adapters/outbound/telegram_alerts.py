"""Gửi alert qua Telegram Bot API.

`core/alerts.py` để sẵn seam này: *"sau này chỉ cần thay `AlertSink` bằng adapter
gửi tới vendor thật, không sửa business rule."* Đây là adapter đó.

Vì sao Telegram chứ không email
-------------------------------
Cần một kênh **ra ngoài app** cho việc nhắc gia hạn, và nó phải tới được điện
thoại của người sẽ gọi khách. Telegram cho một bot gửi tin không cần hạ tầng mail,
không cần lo deliverability, không có thư mục spam. Email thì cần cả ba.

Không cấu hình thì tự tắt, không ném
------------------------------------
Thiếu token là trạng thái bình thường ở local và trong test. Một adapter thông báo
ném lỗi khi chưa cấu hình sẽ làm đổ đúng cái task mà nó chỉ đóng vai phụ — và một
lượt nhắc gia hạn không gửi được không được phép làm chết scheduler.

Cùng lý do đó, lỗi mạng chỉ được **log** rồi bỏ qua: Telegram sập không phải sự
cố của Havi, và thử lại vô hạn một thông báo đã cũ thì vô nghĩa.
"""

import logging

import httpx

from core.alerts import Alert, AlertSink, LoggingAlertSink
from core.structured_logging import log_json

logger = logging.getLogger("havi.alert.telegram")

_API = "https://api.telegram.org"
_TIMEOUT_SECONDS = 10

#: Emoji theo mức độ — để mắt phân loại trước khi đọc chữ, vì đội vận hành đọc
#: kênh này trên điện thoại giữa lúc đang làm việc khác.
_SEVERITY_MARK = {"warning": "⚠️", "error": "🔴", "critical": "🚨"}


class TelegramAlertSink(AlertSink):
    """Gửi alert vào một chat Telegram, và **luôn** log song song.

    Log song song chứ không thay thế: Telegram là kênh để người đọc, log là kênh
    để tra lại. Gửi thành công mà không có dấu vết trong log thì sau này không
    dựng lại được đã cảnh báo những gì.
    """

    def __init__(self, *, bot_token: str, chat_id: str) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._fallback = LoggingAlertSink()

    @property
    def configured(self) -> bool:
        return bool(self._bot_token and self._chat_id)

    async def send(self, alert: Alert) -> None:
        await self._fallback.send(alert)

        if not self.configured:
            return

        mark = _SEVERITY_MARK.get(alert.severity, "•")
        text = f"{mark} {alert.summary}"
        if alert.fields:
            details = "\n".join(f"· {key}: {value}" for key, value in alert.fields.items())
            text = f"{text}\n{details}"

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{_API}/bot{self._bot_token}/sendMessage",
                    json={
                        "chat_id": self._chat_id,
                        "text": text,
                        # Không dùng parse_mode: tên thương hiệu của khách có thể
                        # chứa `_` hay `*`, và Telegram sẽ từ chối cả tin nhắn vì
                        # Markdown không hợp lệ. Chữ thường không bao giờ hỏng.
                        "disable_web_page_preview": True,
                    },
                )
            if response.status_code >= 400:
                log_json(
                    logger,
                    logging.WARNING,
                    "alert.telegram_rejected",
                    status_code=response.status_code,
                    alert_type=alert.type,
                )
        except httpx.HTTPError as exc:
            # Telegram sập không phải sự cố của Havi. Log rồi đi tiếp.
            log_json(
                logger,
                logging.WARNING,
                "alert.telegram_unreachable",
                error=str(exc)[:200],
                alert_type=alert.type,
            )
