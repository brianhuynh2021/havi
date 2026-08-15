"""Rate limit — chạy thật trên Redis.

Không mock Redis: thứ cần kiểm ở đây (INCR đếm đúng, EXPIRE đặt TTL, key hết hạn
thì reset) là hành vi của Redis, mock đi thì test chỉ kiểm cái mock.

Test đi qua limiter trực tiếp thay vì qua HTTP: conftest tắt rate limit cho cả
suite (nếu không, mọi test gọi `/auth/login` sẽ đỏ sau lượt thứ 11 — và đỏ theo
thứ tự chạy nên rất khó truy). Phần dây nối vào endpoint kiểm ở
`TestGanVaoEndpoint` bằng cách đọc dependency của route.
"""

import uuid
from contextlib import asynccontextmanager

import pytest
from redis.asyncio import Redis

from adapters.ratelimit import NullRateLimiter, RateLimitRule, RedisRateLimiter
from core.alerts import Alert, AlertSink
from core.config import get_settings
from domain.policies import rate_limits

pytestmark = pytest.mark.anyio


@asynccontextmanager
async def limiter_scope():
    """Limiter dùng Redis thật, client mở/đóng ngay trong test.

    Cố ý **không** dùng fixture: `asyncio_mode = "auto"` khiến pytest-asyncio
    nhận async fixture, còn `pytestmark = anyio` chạy test trên loop của anyio —
    hai loop khác nhau, và `redis.asyncio` gắn connection pool vào loop lúc tạo,
    nên mọi lệnh Redis ném "attached to a different loop".

    Lỗi đó lại bị `hit()` bắt và fail-open (đúng thiết kế), nên test **không** đỏ
    ở chỗ kết nối mà đỏ ở một assertion số học trông như bug của limiter. Mở
    client trong thân test là cách chắc chắn nhất để không lặp lại chuyện đó.

    Prefix riêng mỗi lượt để các test không đè key của nhau, và không đụng key
    thật của app đang chạy local.
    """
    client = Redis.from_url(get_settings().redis_url)
    try:
        await client.ping()
    except Exception:  # pragma: no cover — Redis chưa chạy
        await client.aclose()
        pytest.skip("Redis chưa chạy (docker compose up -d)")

    prefix = f"havi:test:{uuid.uuid4().hex[:8]}"
    try:
        yield RedisRateLimiter(client, prefix=prefix)
        keys = [k async for k in client.scan_iter(match=f"{prefix}:*")]
        if keys:
            await client.delete(*keys)
    finally:
        await client.aclose()


def _identity() -> str:
    return uuid.uuid4().hex[:12]


class RecordingAlerts(AlertSink):
    def __init__(self) -> None:
        self.sent: list[Alert] = []

    async def send(self, alert: Alert) -> None:
        self.sent.append(alert)


class TestDemVaChan:
    async def test_cho_qua_dung_so_lan_roi_chan(self):
        async with limiter_scope() as limiter:
            rule = RateLimitRule(limit=3, window_seconds=60)
            who = _identity()

            verdicts = [await limiter.hit(rule_name="t", identity=who, rule=rule) for _ in range(4)]

            assert [v.allowed for v in verdicts] == [True, True, True, False]

    async def test_remaining_giam_dan_va_khong_am(self):
        async with limiter_scope() as limiter:
            rule = RateLimitRule(limit=2, window_seconds=60)
            who = _identity()

            first = await limiter.hit(rule_name="t", identity=who, rule=rule)
            second = await limiter.hit(rule_name="t", identity=who, rule=rule)
            third = await limiter.hit(rule_name="t", identity=who, rule=rule)

            assert (first.remaining, second.remaining) == (1, 0)
            assert third.remaining == 0, "remaining không được âm — UI hiện số này"

    async def test_hai_identity_dem_rieng(self):
        """Chủ tiệm A dùng hết hạn mức không được chặn chủ tiệm B."""
        async with limiter_scope() as limiter:
            rule = RateLimitRule(limit=1, window_seconds=60)
            a, b = _identity(), _identity()

            await limiter.hit(rule_name="t", identity=a, rule=rule)
            blocked_a = await limiter.hit(rule_name="t", identity=a, rule=rule)
            fresh_b = await limiter.hit(rule_name="t", identity=b, rule=rule)

            assert blocked_a.allowed is False
            assert fresh_b.allowed is True

    async def test_hai_rule_khac_nhau_khong_de_key_cua_nhau(self):
        """Key gồm cả tên rule: dùng hết hạn mức login không được chặn luôn
        upload."""
        async with limiter_scope() as limiter:
            rule = RateLimitRule(limit=1, window_seconds=60)
            who = _identity()

            await limiter.hit(rule_name="login", identity=who, rule=rule)
            blocked = await limiter.hit(rule_name="login", identity=who, rule=rule)
            other_rule = await limiter.hit(rule_name="upload", identity=who, rule=rule)

            assert blocked.allowed is False
            assert other_rule.allowed is True


class TestTTL:
    async def test_key_luon_co_ttl(self):
        """Key không TTL là sống mãi — người đó bị chặn vĩnh viễn. EXPIRE gọi mỗi
        lượt (không chỉ lượt đầu) chính là để tránh race làm mất TTL."""
        async with limiter_scope() as limiter:
            rule = RateLimitRule(limit=5, window_seconds=120)
            who = _identity()

            await limiter.hit(rule_name="t", identity=who, rule=rule)
            await limiter.hit(rule_name="t", identity=who, rule=rule)

            redis = limiter._redis
            keys = [k async for k in redis.scan_iter(match=f"{limiter._prefix}:*")]
            assert keys, "không tìm thấy key nào"
            for key in keys:
                ttl = await redis.ttl(key)
                assert 0 < ttl <= 120, f"TTL bất thường: {ttl}"

    async def test_retry_after_luon_duong_khi_bi_chan(self):
        """Trả 0 hay số âm thì client không biết chờ bao lâu — header
        `Retry-After` phải dùng được."""
        async with limiter_scope() as limiter:
            rule = RateLimitRule(limit=1, window_seconds=45)
            who = _identity()

            await limiter.hit(rule_name="t", identity=who, rule=rule)
            blocked = await limiter.hit(rule_name="t", identity=who, rule=rule)

            assert blocked.allowed is False
            assert 0 < blocked.retry_after <= 45

    async def test_het_cua_so_thi_dem_lai_tu_dau(self):
        """Xoá key = mô phỏng cửa sổ hết hạn (nhanh hơn chờ TTL thật)."""
        async with limiter_scope() as limiter:
            rule = RateLimitRule(limit=1, window_seconds=60)
            who = _identity()

            await limiter.hit(rule_name="t", identity=who, rule=rule)
            assert (await limiter.hit(rule_name="t", identity=who, rule=rule)).allowed is False

            await limiter._redis.delete(f"{limiter._prefix}:t:{who}")

            assert (await limiter.hit(rule_name="t", identity=who, rule=rule)).allowed is True


class TestRedisHongThiChoQua:
    async def test_redis_chet_khong_lam_chet_app(self):
        """Fail-open có chủ ý: rate limit là lớp bảo vệ, không phải chức năng
        chính. Fail-closed thì Redis chết là app ngừng hoạt động — biến một sự cố
        hạ tầng thành outage toàn phần.

        Đánh đổi: trong lúc Redis chết thì không có giới hạn, nên phải có alert
        cho Redis (ROADMAP Tuần 8).
        """
        # Cổng không có ai lắng nghe → mọi lệnh Redis ném.
        alerts = RecordingAlerts()
        broken = RedisRateLimiter(Redis.from_url("redis://127.0.0.1:1/0"), alerts=alerts)

        verdict = await broken.hit(
            rule_name="t", identity="x", rule=RateLimitRule(limit=1, window_seconds=60)
        )

        assert verdict.allowed is True
        assert alerts.sent[0].type == "redis.rate_limit_fail_open"
        assert alerts.sent[0].severity == "critical"


class TestNullLimiter:
    async def test_khong_bao_gio_chan(self):
        rule = RateLimitRule(limit=1, window_seconds=60)
        limiter = NullRateLimiter()
        for _ in range(5):
            assert (await limiter.hit(rule_name="t", identity="x", rule=rule)).allowed


class TestCauHinh:
    def test_moi_rule_deu_co_gioi_han_duong(self):
        """Rule với limit 0 sẽ chặn mọi request — endpoint chết mà không ai hiểu vì
        sao. window 0 thì TTL không hợp lệ."""
        rules = {
            name: value
            for name, value in vars(rate_limits).items()
            if isinstance(value, RateLimitRule)
        }
        assert rules, "không tìm thấy rule nào — file rate_limits.py trống?"
        for name, rule in rules.items():
            assert rule.limit > 0, f"{name} có limit={rule.limit}"
            assert rule.window_seconds > 0, f"{name} có window={rule.window_seconds}"

    def test_dat_lai_mat_khau_chat_hon_dang_nhap(self):
        """Mỗi lượt xin mã gửi một email thật — tốn tiền, và spam hộp thư người
        khác nếu bị lợi dụng."""
        assert rate_limits.AUTH_PASSWORD_RESET.limit < rate_limits.AUTH_LOGIN.limit


class TestGanVaoEndpoint:
    """Rule khai ra mà quên gắn vào route thì không chặn gì cả — và không có dấu
    hiệu nào.

    Kiểm bằng cách **gọi thật** cho tới khi bị 429, không phải bằng cách đọc
    `route.dependencies`: cấu trúc route là nội bộ của FastAPI (bản này bọc router
    trong `_IncludedRouter` private), nên test dựa vào đó sẽ vỡ khi nâng version
    mà endpoint vẫn đang được bảo vệ đúng.

    Suite bật `HAVI_DISABLE_RATE_LIMIT`, nên phải override dependency bằng limiter
    Redis thật cho riêng các test này.
    """

    async def _with_real_limiter(self, client, limiter):
        from api.deps import _rate_limiter

        app = client._transport.app  # type: ignore[attr-defined]
        app.dependency_overrides[_rate_limiter] = lambda: limiter

    async def test_dang_nhap_bi_chan_sau_qua_nhieu_lan_sai(self, client):
        """Không có giới hạn thì một script thử vài nghìn mật khẩu một phút."""
        async with limiter_scope() as limiter:
            await self._with_real_limiter(client, limiter)
            body = {"email": "khong-ton-tai@havi.vn", "password": "sai-mat-khau"}

            statuses = [
                (await client.post("/auth/login/email", json=body)).status_code
                for _ in range(rate_limits.AUTH_LOGIN.limit + 1)
            ]

            assert statuses[-1] == 429, f"không bị chặn: {statuses}"
            # Các lượt trước phải là 401 (sai mật khẩu), không phải 429 — chặn quá
            # sớm là chặn oan người gõ sai vài lần.
            assert set(statuses[:-1]) == {401}, statuses

    async def test_429_kem_retry_after(self, client):
        async with limiter_scope() as limiter:
            await self._with_real_limiter(client, limiter)
            body = {"email": "x@havi.vn", "password": "sai"}
            for _ in range(rate_limits.AUTH_LOGIN.limit):
                await client.post("/auth/login/email", json=body)

            blocked = await client.post("/auth/login/email", json=body)

            assert blocked.status_code == 429
            assert int(blocked.headers["Retry-After"]) > 0

    async def test_dang_ky_cung_bi_chan(self, client):
        """Sign-up dùng chung rule với login, và cần chặn vì lý do khác: không có
        giới hạn thì một script tạo hàng nghìn tài khoản rác, mỗi cái một workspace
        trong DB.

        Test này thêm sau khi mutation test lộ ra khoảng trống: bỏ rate limit khỏi
        `/auth/sign-up` mà cả suite vẫn xanh.
        """
        async with limiter_scope() as limiter:
            await self._with_real_limiter(client, limiter)

            statuses = []
            for i in range(rate_limits.AUTH_LOGIN.limit + 1):
                response = await client.post(
                    "/auth/sign-up",
                    json={
                        "name": "Chị Hương",
                        "email": f"spam{i}-{uuid.uuid4().hex[:6]}@havi.vn",
                        "password": "matkhau123",
                    },
                )
                statuses.append(response.status_code)

            assert statuses[-1] == 429, f"không bị chặn: {statuses}"
            assert set(statuses[:-1]) == {201}, statuses

    async def test_xin_ma_dat_lai_mat_khau_bi_chan_chat_hon(self, client):
        """Mỗi lượt gửi một email thật — tốn tiền, và spam hộp thư người khác nếu
        bị lợi dụng."""
        async with limiter_scope() as limiter:
            await self._with_real_limiter(client, limiter)
            body = {"email": "ai-do@havi.vn"}

            statuses = [
                (await client.post("/auth/password-reset/request", json=body)).status_code
                for _ in range(rate_limits.AUTH_PASSWORD_RESET.limit + 1)
            ]

            assert statuses[-1] == 429, f"không bị chặn: {statuses}"

    async def test_endpoint_chi_doc_khong_bi_chan(self, client):
        """Không gắn bừa: GET chỉ đọc DB, chặn oan thì chủ tiệm không xem được
        hàng chờ duyệt. Gọi nhiều hơn hạn mức của mọi rule vẫn phải qua."""
        async with limiter_scope() as limiter:
            await self._with_real_limiter(client, limiter)
            token = await _onboard(client, email=f"rl{uuid.uuid4().hex[:8]}@havi.vn")

            statuses = [
                (
                    await client.get("/content", headers={"Authorization": f"Bearer {token}"})
                ).status_code
                for _ in range(rate_limits.CONTENT_JOB.limit + 3)
            ]

            assert 429 not in statuses, statuses


async def _onboard(client, *, email: str) -> str:
    """Đăng ký + activate workspace, trả access token."""
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chị Hương", "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    tokens = signup.json()
    create = await client.post(
        "/workspaces",
        json={"name": "Spa An Nhiên", "industry": "spa"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert create.status_code == 201, create.text
    refreshed = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200, refreshed.text
    return refreshed.json()["access_token"]
