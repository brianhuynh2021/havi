"""Lỗi dùng chung cho tầng API."""

from fastapi import HTTPException, status

from core.content_state import InvalidTransitionError


class NotImplementedEndpoint(HTTPException):
    """Endpoint đã khoá contract nhưng chưa có implementation.

    Giữ endpoint trong OpenAPI để `apps/web` sinh được TypeScript client và dựng UI
    bằng fixture trước, đúng thứ tự triển khai trong SYSTEM_ARCHITECTURE.md §4.
    """

    def __init__(self, detail: str = "Endpoint chưa được implement") -> None:
        super().__init__(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=detail)


def transition_conflict(error: InvalidTransitionError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
