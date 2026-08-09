"""Structured logging helpers.

Log vận hành cần machine-readable để grep/ship sang hệ thống log sau này. Helper
này cố ý nhỏ: emit một JSON object trên một dòng, không chạm body/query/header
nhạy cảm.
"""

import json
import logging
from typing import Any


def log_json(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    payload = {"event": event, **fields}
    logger.log(
        level,
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
    )
