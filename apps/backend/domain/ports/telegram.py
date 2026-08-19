"""Port cho dịch vụ gửi thông báo Telegram — xem ROADMAP §1 (Unified Inbox & Lead Care)."""

from typing import Protocol


class TelegramNotifierPort(Protocol):
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
        """Gửi tin nhắn cảnh báo chuông reo tức thì về Telegram của chủ tiệm."""
        ...
