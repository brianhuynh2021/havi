"""Liveness/readiness và `/metrics`.

Trọng tâm là điều bản cũ làm sai: `/health` trả `{"status": "ok"}` hardcode, nên
Postgres sập nó vẫn báo khoẻ và load balancer vẫn đổ traffic vào.
"""

import pytest
from httpx import AsyncClient


class TestLiveness:
    @pytest.mark.asyncio
    async def test_health_khong_can_auth(self, client: AsyncClient) -> None:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_khong_cham_database(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Liveness phải xanh dù DB chết.

        Nếu nó phụ thuộc Postgres thì một lần DB chớp nhoáng sẽ khiến
        orchestrator restart *mọi* pod đang khoẻ — lúc DB trở lại thì không còn
        gì để phục vụ. Test này khoá hành vi đó lại.
        """
        import api.routers.health as health_module

        async def _boom() -> None:
            raise ConnectionError("postgres down")

        monkeypatch.setattr(health_module, "_check_postgres", _boom)

        res = await client.get("/health")

        assert res.status_code == 200


class TestReadiness:
    @pytest.mark.asyncio
    async def test_ready_bao_ok_khi_postgres_song(self, client: AsyncClient) -> None:
        res = await client.get("/health/ready")

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        assert {c["name"] for c in body["checks"]} == {"postgres", "redis"}

    @pytest.mark.asyncio
    async def test_postgres_chet_thi_tra_503(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Đây là bug đang sửa: probe phải đỏ khi backend không phục vụ được."""
        import api.routers.health as health_module

        async def _boom() -> None:
            raise ConnectionError("postgres down")

        monkeypatch.setattr(health_module, "_check_postgres", _boom)

        res = await client.get("/health/ready")

        assert res.status_code == 503
        assert res.json()["status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_redis_chet_khong_keo_sap_readiness(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Redis chỉ làm Havi xuống cấp, không làm nó mất khả năng phục vụ.

        Gộp Redis vào cùng một cờ boolean với Postgres sẽ khiến Redis nhấp nháy
        rút mọi pod ra khỏi load balancer — đúng loại sự cố tự gây mà readiness
        probe lẽ ra phải ngăn.
        """
        import api.routers.health as health_module

        async def _boom(url: str) -> None:
            raise ConnectionError("redis down")

        monkeypatch.setattr(health_module, "_check_redis", _boom)

        res = await client.get("/health/ready")

        assert res.status_code == 200
        redis_check = next(c for c in res.json()["checks"] if c["name"] == "redis")
        assert redis_check["ok"] is False

    @pytest.mark.asyncio
    async def test_khong_lo_chi_tiet_ket_noi(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Endpoint này không cần JWT, mà message của driver hay chứa host/user/db."""
        import api.routers.health as health_module

        async def _boom() -> None:
            raise ConnectionError("could not connect to host=10.0.0.5 user=havi_admin")

        monkeypatch.setattr(health_module, "_check_postgres", _boom)

        res = await client.get("/health/ready")

        assert "10.0.0.5" not in res.text
        assert "havi_admin" not in res.text
        pg = next(c for c in res.json()["checks"] if c["name"] == "postgres")
        assert pg["error"] == "ConnectionError"


class TestMetrics:
    @pytest.mark.asyncio
    async def test_metrics_tra_dinh_dang_prometheus(self, client: AsyncClient) -> None:
        await client.get("/health")
        res = await client.get("/metrics")

        assert res.status_code == 200
        assert "havi_http_requests_total" in res.text
        assert "havi_http_request_duration_seconds_bucket" in res.text

    @pytest.mark.asyncio
    async def test_label_path_la_route_template_khong_phai_url_that(
        self, client: AsyncClient
    ) -> None:
        """Chỗ metrics HTTP hay hỏng nhất.

        Dùng URL thật thì mỗi UUID sinh một time series sống mãi, và Prometheus
        phình tới OOM sau vài ngày. Test này chốt lại rằng cardinality bị chặn.
        """
        await client.get("/workspaces/11111111-1111-1111-1111-111111111111")
        res = await client.get("/metrics")

        assert "11111111-1111-1111-1111-111111111111" not in res.text

    @pytest.mark.asyncio
    async def test_url_khong_khop_route_gop_vao_mot_nhan(
        self, client: AsyncClient
    ) -> None:
        """Bot quét `/.env`, `/wp-login.php`… vô hạn — không được thành series riêng."""
        await client.get("/khong-ton-tai-mot-duong-nao")
        res = await client.get("/metrics")

        assert "khong-ton-tai-mot-duong-nao" not in res.text
        assert "<unmatched>" in res.text
