"""Adapter gửi tin nhắn cảnh báo Hot Lead qua Telegram Bot API."""

import logging

import httpx

from core.config import Settings
from domain.ports.telegram import TelegramNotifierPort

logger = logging.getLogger(__name__)


class TelegramNotifier(TelegramNotifierPort):
    def __init__(self, settings: Settings) -> None:
        self._bot_token = getattr(settings, "telegram_bot_token", None) or "MOCK_TELEGRAM_BOT_TOKEN"
        self._default_chat_id = getattr(settings, "telegram_default_chat_id", None) or "demo_chat_id"

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
        target_chat = chat_id or self._default_chat_id
        if not target_chat:
            logger.warning("Telegram chat_id chưa được cấu hình, bỏ qua thông báo.")
            return False

        clean_phone = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        note_text = f'💬 Nhu cầu: "{message}"\n' if message else ""

        html_body = (
            f"🔔 <b>[HAVI HOT LEAD] CÓ KHÁCH CẦN TƯ VẤN GẤP!</b>\n\n"
            f"👤 Khách hàng: <b>{customer_name}</b>\n"
            f"📱 Số điện thoại: <code>{phone}</code>\n"
            f"{note_text}"
            f"📍 Kênh: <b>{platform}</b>\n"
            f"--------------------------------------------------\n"
            f"👉 <a href='tel:{clean_phone}'>📞 BẤM GỌI ĐIỆN NGAY</a>   <a href='https://zalo.me/{clean_phone}'>💬 BẤM MỞ CHAT ZALO</a>"
        )

        if not self._bot_token or self._bot_token.startswith("MOCK_"):
            logger.info("Telegram Mock Dispatch: Gửi thông báo thành công tới chat_id=%s\n%s", target_chat, html_body)
            return True

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        payload = {
            "chat_id": target_chat,
            "text": html_body,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    return True
                logger.error("Telegram API trả về lỗi: status=%s body=%s", res.status_code, res.text)
                return False
        except Exception as exc:
            logger.error("Lỗi khi kết nối Telegram API: %s", exc)
            return False
