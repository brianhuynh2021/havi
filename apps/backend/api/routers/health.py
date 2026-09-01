"""Health check — endpoint duy nhất không cần JWT, dùng cho probe khi deploy.

Hai endpoint, hai câu hỏi khác nhau — đừng gộp:

- `/health` (**liveness**): "process này còn sống không?" Không chạm dependency.
  Orchestrator dùng nó để quyết định *restart*. Cho nó phụ thuộc Postgres là tự
  bắn chân: DB chớp nhoáng 5 giây thì k8s giết sạch mọi pod đang khoẻ, và lúc DB
  trở lại thì không còn gì để phục vụ.

- `/health/ready` (**readiness**): "có nên đổ traffic vào không?" Ping thật
  Postgres và Redis. Load balancer dùng nó để *rút pod ra khỏi vòng*, không
  restart.

Bản trước chỉ có `/health` và trả `{"status": "ok"}` **hardcode** — nghĩa là
Postgres sập thì nó vẫn báo "ok" và LB vẫn đổ request vào một backend không phục
vụ được gì. Một probe luôn xanh thì tệ hơn không có probe: nó khiến người vận
hành tin là tầng app còn tốt trong khi sự thật ngược lại.
"""

import asyncio
import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from adapters.persistence.db import session_scope
from api.deps import SettingsDep
from core.schemas import HaviModel
from core.structured_logging import log_json

logger = logging.getLogger("havi.health")

router = APIRouter(tags=["health"])

#: Probe phải trả lời nhanh hơn chu kỳ probe của orchestrator, nếu không mọi lần
#: kiểm đều timeout và pod bị rút ra vì lý do sai. Ngắn hơn timeout mặc định của
#: HTTP client rất nhiều — probe là câu hỏi "còn sống?", không phải một query thật.
_PROBE_TIMEOUT_SECONDS = 3.0


class HealthResponse(HaviModel):
    status: str
    env: str
    version: str


class ReadinessCheck(HaviModel):
    name: str
    ok: bool
    #: Chỉ có khi lỗi. Là tên loại ngoại lệ, **không** phải str(exc): message của
    #: driver Postgres hay chứa host/user/database, mà endpoint này không cần JWT.
    error: str | None = None
    duration_ms: int


class ReadinessResponse(HaviModel):
    status: str
    env: str
    version: str
    checks: list[ReadinessCheck]


@router.get("/health", response_model=HealthResponse)
def health(settings: SettingsDep) -> HealthResponse:
    """Liveness — cố ý không chạm dependency nào. Xem docstring module."""
    return HealthResponse(status="ok", env=settings.env, version="0.1.0")


async def _check_postgres() -> None:
    async with session_scope() as session:
        await session.execute(text("SELECT 1"))


async def _check_redis(redis_url: str) -> None:
    # Import tại chỗ: redis là extra (`--extra queue`), và liveness không được
    # phụ thuộc việc nó có được cài hay không.
    from redis.asyncio import Redis

    client = Redis.from_url(redis_url)
    try:
        await client.ping()
    finally:
        await client.aclose()


async def _run_check(name: str, coro) -> ReadinessCheck:  # noqa: ANN001
    started = asyncio.get_running_loop().time()

    def elapsed() -> int:
        return round((asyncio.get_running_loop().time() - started) * 1000)

    try:
        await asyncio.wait_for(coro, timeout=_PROBE_TIMEOUT_SECONDS)
    except TimeoutError:
        # Timeout tách riêng khỏi lỗi khác: "Postgres chậm quá" và "Postgres từ
        # chối kết nối" dẫn tới hai hành động vận hành khác nhau.
        return ReadinessCheck(name=name, ok=False, error="timeout", duration_ms=elapsed())
    except Exception as exc:
        return ReadinessCheck(
            name=name, ok=False, error=type(exc).__name__, duration_ms=elapsed()
        )
    return ReadinessCheck(name=name, ok=True, duration_ms=elapsed())


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(settings: SettingsDep, response: Response) -> ReadinessResponse:
    """Readiness — ping Postgres và Redis, trả 503 khi có cái nào chết.

    Chạy song song: hai lần chờ tuần tự thì probe chậm gấp đôi, và với timeout
    3 giây mỗi cái thì tổng vượt quá chu kỳ probe thường dùng.

    **Redis không chặn readiness.** Nó phục vụ rate-limit và job queue; mất Redis
    thì Havi xuống cấp (rate-limit rơi về `NullRateLimiter`) chứ không mất khả
    năng phục vụ. Postgres thì khác: không có nó thì không request nào có nghĩa.
    Trộn hai mức độ này vào một cờ boolean sẽ khiến Redis nhấp nháy kéo sập cả
    site — đúng loại sự cố tự gây mà readiness probe lẽ ra phải ngăn.
    """
    checks = await asyncio.gather(
        _run_check("postgres", _check_postgres()),
        _run_check("redis", _check_redis(settings.redis_url)),
    )
    critical = {"postgres"}
    ready = all(check.ok for check in checks if check.name in critical)

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        log_json(
            logger,
            logging.ERROR,
            "health.not_ready",
            failed=[check.name for check in checks if not check.ok],
        )
    elif not all(check.ok for check in checks):
        log_json(
            logger,
            logging.WARNING,
            "health.degraded",
            failed=[check.name for check in checks if not check.ok],
        )

    return ReadinessResponse(
        status="ok" if ready else "unavailable",
        env=settings.env,
        version="0.1.0",
        checks=list(checks),
    )
