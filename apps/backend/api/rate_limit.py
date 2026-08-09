"""Dependency áp rate limit cho endpoint.

Tách khỏi `api/deps.py` vì nó là *middleware nghiệp vụ* (chặn request), không
phải injection của service — và để `deps.py` không phình thêm.

Hai kiểu định danh, chọn theo thứ bị lạm dụng:

- **Theo IP** cho endpoint public (login, đặt lại mật khẩu): chưa có JWT nên
  không có gì khác để đếm. Kẻ brute force đổi email mỗi lượt, nên đếm theo email
  chặn được đúng số 0.
- **Theo workspace** cho endpoint đã đăng nhập (upload, content job): thứ tiêu
  tiền là workspace, và một chủ tiệm đổi mạng (4G ↔ wifi) không được reset hạn mức.
"""

import logging
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from adapters.ratelimit import RateLimitRule
from api.deps import RateLimiterDep, WorkspaceDep

logger = logging.getLogger(__name__)

TOO_MANY = "Chị thao tác hơi nhanh — đợi một chút rồi thử lại giúp em nhé."


def _client_ip(request: Request) -> str:
    """IP của client, ưu tiên `X-Forwarded-For` khi chạy sau proxy.

    Lấy IP **đầu tiên** trong chuỗi: đó là client thật, các IP sau là proxy.
    Không có header thì dùng peer address.

    Lưu ý an toàn: header này do client gửi nên giả mạo được — chỉ tin khi API
    chạy sau một reverse proxy mà mình kiểm soát (proxy sẽ ghi đè header). Chạy
    trần ra internet thì kẻ tấn công đổi header mỗi lượt là thoát giới hạn.
    Ghi lại ở đây để lúc dựng staging không quên cấu hình proxy (ROADMAP Tuần 9).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def limit_by_ip(rule_name: str, rule: RateLimitRule) -> Callable:
    """Dependency giới hạn theo IP — cho endpoint public."""

    async def _guard(request: Request, limiter: RateLimiterDep) -> None:
        verdict = await limiter.hit(
            rule_name=rule_name, identity=_client_ip(request), rule=rule
        )
        if not verdict.allowed:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                TOO_MANY,
                headers={"Retry-After": str(verdict.retry_after)},
            )

    return Depends(_guard)


def limit_by_workspace(rule_name: str, rule: RateLimitRule) -> Callable:
    """Dependency giới hạn theo workspace — cho endpoint đã đăng nhập."""

    async def _guard(workspace_id: WorkspaceDep, limiter: RateLimiterDep) -> None:
        verdict = await limiter.hit(
            rule_name=rule_name, identity=str(workspace_id), rule=rule
        )
        if not verdict.allowed:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                TOO_MANY,
                headers={"Retry-After": str(verdict.retry_after)},
            )

    return Depends(_guard)
