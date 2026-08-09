"""Request/correlation id context.

HTTP request, Celery task và event logging nằm ở các lớp khác nhau. `contextvars`
cho phép repository/log code đọc request id hiện tại mà không phải truyền tham số
qua mọi hàm không liên quan.
"""

from contextvars import ContextVar
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-ID"

_request_id: ContextVar[str | None] = ContextVar("havi_request_id", default=None)


def new_request_id() -> str:
    return uuid4().hex


def sanitize_request_id(value: str | None) -> str:
    """Chấp nhận client-provided id nếu gọn và log-safe, còn lại tự phát id mới."""
    if value is None:
        return new_request_id()
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 80:
        return new_request_id()
    if not all(ch.isalnum() or ch in "-_." for ch in cleaned):
        return new_request_id()
    return cleaned


def set_request_id(value: str):
    return _request_id.set(value)


def reset_request_id(token) -> None:  # noqa: ANN001 - token type is private to contextvars
    _request_id.reset(token)


def get_request_id() -> str | None:
    return _request_id.get()
