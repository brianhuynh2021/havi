"""Structured logging helpers.

Log vận hành cần machine-readable để grep/ship sang hệ thống log sau này. Helper
này cố ý nhỏ: emit một JSON object trên một dòng, không chạm body/query/header
nhạy cảm.
"""

import json
import logging
from typing import Any

from core.request_context import get_request_id


class RequestIdFilter(logging.Filter):
    """Logging filter tự động bổ sung request_id từ contextvar vào LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        req_id = get_request_id()
        if req_id and not hasattr(record, "request_id"):
            record.request_id = req_id
        return True


def log_json(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    req_id = fields.pop("request_id", None) or get_request_id()
    payload = {"event": event, **({"request_id": req_id} if req_id else {}), **fields}
    logger.log(
        level,
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
    )
