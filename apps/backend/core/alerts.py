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
