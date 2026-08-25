"""Chuông Hot Lead qua Telegram Bot API.

Một luật chi phối cả file: **`True` nghĩa là Telegram đã nhận tin, không phải
"code chạy tới đây mà không lỗi".**

Bản trước vi phạm đúng điều đó. Khi thiếu token, nó rơi về nhánh mock, ghi log
"Gửi thông báo thành công" rồi trả `True`. Khách để lại số điện thoại, hệ thống
báo đã bắn chuông, và không có gì được gửi đi — lead nguội mất mà không ai biết.
Cấu hình rỗng giờ bị chặn ngay lúc khởi động ở staging/production
(`Settings._force_real_telegram_outside_local`); ở local nó vẫn ghi log để chạy
tay không cần bot thật, nhưng trả `False` và nói rõ là chưa gửi.
"""

import logging

import httpx

from core.config import Settings
from domain.ports.telegram import TelegramNotifierPort

logger = logging.getLogger(__name__)

#: Telegram cắt tin nhắn dài hơn ngưỡng này. Cắt chủ động ở phía Havi để lỗi
#: hiện ra dưới dạng nội dung ngắn đi, chứ không phải một lần gửi hỏng hoàn toàn.
_MAX_MESSAGE_CHARS = 4096

#: Chuông reo phải nhanh hơn sự kiên nhẫn của khách. Quá ngưỡng này thì coi như
#: hỏng và ghi log — chờ lâu hơn không làm lead ấm lại.
_TIMEOUT_SECONDS = 5.0


def _escape_html(value: str) -> str:
    """Thoát ký tự HTML trước khi ghép vào `parse_mode=HTML`.

    Tên khách và nội dung tin nhắn đến từ Facebook, tức là dữ liệu ngoài. Một
    cái tên chứa `<` làm Telegram từ chối cả tin nhắn với lỗi parse — nghĩa là
    đúng những lead có tên lạ lại là những lead không bao giờ reo chuông.
    """
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


class TelegramNotifier(TelegramNotifierPort):
    def __init__(self, settings: Settings) -> None:
        self._bot_token = (settings.telegram_bot_token or "").strip()
        self._default_chat_id = (settings.telegram_default_chat_id or "").strip()
        #: Chỉ đúng ở local, nơi validator cho phép cấu hình rỗng.
        self._configured = bool(self._bot_token and self._default_chat_id)

    async def send_hot_lead_alert(
        self,
        *,
        chat_id: str | None = None,
        shop_name: str,
        customer_name: str,
        phone: str,
        message: str | None = None,
        platform: str = "Facebook Fanpage",
    ) -> bool:
        """Trả `True` **chỉ khi** Telegram xác nhận đã nhận tin nhắn."""
        target_chat = (chat_id or self._default_chat_id).strip()
        body = self._compose(
            shop_name=shop_name,
            customer_name=customer_name,
            phone=phone,
            message=message,
            platform=platform,
        )

        if not self._configured or not target_chat:
            # Chỉ xảy ra ở local — staging/production đã bị chặn từ lúc khởi
            # động. Ghi nguyên nội dung ra log để chạy tay vẫn xem được, nhưng
            # trả False vì chuông thật sự chưa reo.
            logger.warning(
                "Telegram chưa cấu hình — KHÔNG gửi chuông Hot Lead. Nội dung lẽ ra gửi:\n%s",
                body,
            )
            return False

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        payload = {
            "chat_id": target_chat,
            "text": body,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                res = await client.post(url, json=payload)
        except Exception as exc:
            logger.error(
                "Không gửi được chuông Hot Lead cho %s (%s): %s", customer_name, phone, exc
            )
            return False

        if res.status_code == 200:
            return True

        # Ghi cả số điện thoại vào log lỗi: đây là lead có thật đang bị bỏ lỡ, và
        # người trực cần đủ thông tin để gọi tay ngay mà không phải tra DB.
        logger.error(
            "Telegram từ chối chuông Hot Lead cho %s (%s): status=%s body=%s",
            customer_name,
            phone,
            res.status_code,
            res.text,
        )
        return False

    def _compose(
        self,
        *,
        shop_name: str,
        customer_name: str,
        phone: str,
        message: str | None,
        platform: str,
    ) -> str:
        """Dựng nội dung chuông. Hai nút bấm gọi/chat là phần đáng giá nhất.

        Người trực đọc tin này trên điện thoại, giữa lúc đang làm việc khác. Mỗi
        thao tác phải gõ lại số điện thoại là một lý do để hoãn — và hoãn một
        lead nóng thì thành lead nguội.
        """
        clean_phone = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        note = (
            f'💬 Nhu cầu: "{_escape_html(message.strip())}"\n'
            if message and message.strip()
            else ""
        )

        body = (
            f"🔔 <b>[{_escape_html(shop_name)}] CÓ KHÁCH CẦN TƯ VẤN GẤP!</b>\n\n"
            f"👤 Khách hàng: <b>{_escape_html(customer_name)}</b>\n"
            f"📱 Số điện thoại: <code>{_escape_html(phone)}</code>\n"
            f"{note}"
            f"📍 Kênh: <b>{_escape_html(platform)}</b>\n"
            f"{'-' * 40}\n"
            f"👉 <a href='tel:{clean_phone}'>📞 GỌI NGAY</a>"
            f"   <a href='https://zalo.me/{clean_phone}'>💬 MỞ CHAT ZALO</a>"
        )
        if len(body) <= _MAX_MESSAGE_CHARS:
            return body

        # Cắt phần nhu cầu chứ không cắt đuôi: số điện thoại và hai nút bấm là
        # thứ duy nhất bắt buộc phải còn nguyên.
        overflow = len(body) - _MAX_MESSAGE_CHARS
        trimmed = (message or "").strip()[: max(0, len(message or "") - overflow - 3)]
        return self._compose(
            shop_name=shop_name,
            customer_name=customer_name,
            phone=phone,
            message=f"{trimmed}…" if trimmed else None,
            platform=platform,
        )
