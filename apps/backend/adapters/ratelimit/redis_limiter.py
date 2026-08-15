"""Rate limit bằng Redis — chặn brute force và spam trước khi nó tốn tiền.

Counter phải nằm **ngoài process**: in-memory thì mỗi worker uvicorn đếm riêng
(chạy 4 worker = giới hạn thật gấp 4 lần khai báo), và restart là mất sạch — kẻ
brute force chỉ cần đợi một lần deploy. Redis đã có trong stack cho Celery.

Thuật toán là **fixed window** (INCR + EXPIRE), không phải sliding window. Đánh
đổi: ngay ranh giới cửa sổ, một kẻ tấn công có thể gửi 2× giới hạn trong khoảnh
khắc (cuối cửa sổ này + đầu cửa sổ sau). Chấp nhận ở pilot vì nó đơn giản, chỉ
tốn 1 round-trip Redis, và mục tiêu ở đây là chặn brute force/spam — không phải
chống DDoS. Sliding window cần sorted set và nhiều lệnh hơn; đổi sau nếu cần,
interface `RateLimiter` không phải sửa.
"""

import logging
from dataclasses import dataclass

from redis.asyncio import Redis

from core.alerts import Alert, AlertSink, LoggingAlertSink

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitRule:
    """`limit` lượt trong `window_seconds` giây."""

    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitVerdict:
    allowed: bool
    remaining: int
    #: Giây còn lại của cửa sổ hiện tại — dùng cho header `Retry-After`.
    retry_after: int


class RedisRateLimiter:
    """Fixed-window counter. Key gồm cả tên rule để hai rule không đè nhau."""

    def __init__(
        self,
        redis: Redis,
        *,
        prefix: str = "havi:rl",
        alerts: AlertSink | None = None,
    ) -> None:
        self._redis = redis
        self._prefix = prefix
        self._alerts = alerts or LoggingAlertSink()

    async def hit(self, *, rule_name: str, identity: str, rule: RateLimitRule) -> RateLimitVerdict:
        """Tính một lượt và trả phán quyết.

        **Redis hỏng thì cho qua (fail-open), không chặn.** Đây là quyết định có
        chủ ý: rate limit là lớp bảo vệ, không phải chức năng chính. Redis chết mà
        fail-closed thì cả app ngừng hoạt động — biến một sự cố hạ tầng thành
        outage toàn phần. Đánh đổi là trong lúc Redis chết thì không có giới hạn,
        nên phải có alert cho Redis (ROADMAP Tuần 8).
        """
        key = f"{self._prefix}:{rule_name}:{identity}"
        try:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            # EXPIRE mỗi lượt, không chỉ lượt đầu: nếu chỉ set khi count==1 thì một
            # race giữa hai request đầu tiên có thể để key không có TTL — sống mãi,
            # và người dùng đó bị chặn vĩnh viễn.
            pipe.expire(key, rule.window_seconds)
            pipe.ttl(key)
            count, _, ttl = await pipe.execute()
        except Exception:
            logger.warning(
                "rate limit: Redis không phản hồi, cho qua request (rule=%s)",
                rule_name,
                exc_info=True,
            )
            await self._alerts.send(
                Alert(
                    type="redis.rate_limit_fail_open",
                    severity="critical",
                    summary="Redis rate limiter không phản hồi; request được cho qua",
                    fields={"rule": rule_name},
                )
            )
            return RateLimitVerdict(allowed=True, remaining=rule.limit, retry_after=0)

        count = int(count)
        # TTL âm (-1 không hạn, -2 key vừa hết) → dùng độ dài cửa sổ làm đáy, đừng
        # trả Retry-After âm hay 0 cho một request đang bị chặn.
        retry_after = int(ttl) if int(ttl) > 0 else rule.window_seconds
        return RateLimitVerdict(
            allowed=count <= rule.limit,
            remaining=max(0, rule.limit - count),
            retry_after=retry_after,
        )


class NullRateLimiter:
    """Không giới hạn gì — dùng trong test để không cần Redis thật.

    Tách thành class riêng thay vì `if settings.testing` rải trong code: chỗ gọi
    không cần biết đang chạy limiter nào.
    """

    async def hit(self, *, rule_name: str, identity: str, rule: RateLimitRule) -> RateLimitVerdict:
        del rule_name, identity
        return RateLimitVerdict(allowed=True, remaining=rule.limit, retry_after=0)
