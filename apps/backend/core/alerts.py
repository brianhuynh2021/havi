"""Operational alerts.

Pilot chưa chốt Sentry/Slack/PagerDuty, nên alert hiện là structured log
`havi.alert`. Sau này chỉ cần thay `AlertSink` bằng adapter gửi tới vendor thật,
không sửa business rule.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

from core.request_context import get_request_id
from core.structured_logging import log_json

AlertSeverity = Literal["warning", "error", "critical"]

logger = logging.getLogger("havi.alert")


@dataclass(frozen=True)
class Alert:
    type: str
    severity: AlertSeverity
    summary: str
    workspace_id: str | None = None
    job_id: str | None = None
    request_id: str | None = None
    fields: dict[str, object] = field(default_factory=dict)


class AlertSink(ABC):
    @abstractmethod
    async def send(self, alert: Alert) -> None: ...


class LoggingAlertSink(AlertSink):
    async def send(self, alert: Alert) -> None:
        level = logging.WARNING if alert.severity == "warning" else logging.ERROR
        log_json(
            logger,
            level,
            "alert",
            type=alert.type,
            severity=alert.severity,
            summary=alert.summary,
            workspace_id=alert.workspace_id,
            job_id=alert.job_id,
            request_id=alert.request_id or get_request_id(),
            **alert.fields,
        )


class TelegramAlertSink(AlertSink):
    """Gửi cảnh báo vận hành tới Telegram nhóm trực ca."""

    def __init__(self, bot_token: str, chat_id: str, *, fallback_logging: bool = True) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._fallback_logging = fallback_logging
        self._logging_sink = LoggingAlertSink()

    async def send(self, alert: Alert) -> None:
        if self._fallback_logging:
            await self._logging_sink.send(alert)

        if not self._bot_token or not self._chat_id:
            return

        icon = "🚨" if alert.severity == "critical" else ("⚠️" if alert.severity == "error" else "ℹ️")
        text = (
            f"{icon} <b>[HAVI ALERT - {alert.severity.upper()}]</b>\n"
            f"<b>Type:</b> <code>{alert.type}</code>\n"
            f"<b>Summary:</b> {alert.summary}\n"
        )
        if alert.workspace_id:
            text += f"<b>Workspace:</b> <code>{alert.workspace_id}</code>\n"
        if alert.job_id:
            text += f"<b>Job:</b> <code>{alert.job_id}</code>\n"
        if alert.request_id:
            text += f"<b>Request ID:</b> <code>{alert.request_id}</code>\n"

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    url,
                    json={
                        "chat_id": self._chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )
        except Exception:
            logger.warning("failed_to_send_telegram_alert", exc_info=True)


def get_alert_sink() -> AlertSink:
    """Trả về AlertSink phù hợp cấu hình."""
    from core.config import get_settings

    settings = get_settings()
    if settings.telegram_bot_token and settings.telegram_default_chat_id:
        return TelegramAlertSink(settings.telegram_bot_token, settings.telegram_default_chat_id)
    return LoggingAlertSink()
