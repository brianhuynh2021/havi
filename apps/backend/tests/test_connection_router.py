"""/connections/* qua HTTP thật — auth scope, redirect callback, và 501/503.

Khác `test_connection_flow.py` (test service/adapter trực tiếp), file này kiểm
đúng phần chỉ tầng HTTP mới lộ ra: callback phải **redirect** chứ không trả
JSON, người dùng bấm "Huỷ" ở Facebook không được rơi vào 422, và JWT của tiệm
này không đọc được kết nối của tiệm kia.
"""

from httpx import AsyncClient

from adapters.oauth.base import OAuthAccount, OAuthClientPort
from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from api.deps import get_connection_service
from application.services.connection_service import ConnectionService
from core.config import get_settings
from core.enums import Platform

PAGE_TOKEN = "EAAG-page-token-bi-mat"


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    """Đăng ký → tạo workspace → refresh để JWT mang active_workspace_id."""
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chị Hương", "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()

    create = await client.post(
        "/workspaces",
        json={"name": "Spa An Nhiên", "industry": "spa"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert create.status_code == 201, create.text

    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    assert refreshed.status_code == 200, refreshed.text
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


class _StubOAuthClient(OAuthClientPort):
    """Facebook giả ở tầng port — router test không cần đụng tới Graph API."""

    def __init__(self, *, configured: bool = True) -> None:
        self._configured = configured

    @property
    def platform(self) -> Platform:
        return Platform.FACEBOOK

    @property
    def is_configured(self) -> bool:
        return self._configured

    def authorization_url(self, *, state: str) -> str:
        return f"https://www.facebook.com/dialog/oauth?state={state}"

    async def exchange_code(self, code: str) -> OAuthAccount:
        return OAuthAccount(
            external_account_id="page-1",
            account_name="Spa An Nhiên",
            access_token=PAGE_TOKEN,
        )


def _override(client: AsyncClient, db_session, *, configured: bool = True) -> None:
    """Thay OAuth client thật bằng stub, giữ nguyên repository và DB session."""
    app = client._transport.app  # type: ignore[attr-defined]

    def _factory() -> ConnectionService:
        return ConnectionService(
            connections=ConnectionRepository(db_session),
            members=WorkspaceMemberRepository(db_session),
            oauth_clients={
                Platform.FACEBOOK: _StubOAuthClient(configured=configured),
                Platform.ZALO_OA: _StubOAuthClient(configured=configured),
            },
            settings=get_settings(),
        )

    app.dependency_overrides[get_connection_service] = _factory


class TestStartOAuth:
    async def test_start_tra_url_va_state(self, client: AsyncClient, db_session):
        token = await _onboard(client, email="conn0001@havi.vn")
        _override(client, db_session)

        response = await client.post(
            "/connections/facebook/start", headers=_headers(token)
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["state"] and body["state"] in body["authorization_url"]

    async def test_start_can_dang_nhap(self, client: AsyncClient):
        assert (await client.post("/connections/facebook/start")).status_code == 401

    async def test_kenh_chua_co_adapter_tra_501(self, client: AsyncClient, db_session):
        """YouTube chưa có adapter — 501 để UI không hiện "đã nối" cho kênh fixture."""
        token = await _onboard(client, email="conn0002@havi.vn")
        _override(client, db_session)

        response = await client.post(
            "/connections/youtube/start", headers=_headers(token)
        )

        assert response.status_code == 501, response.text

    async def test_thieu_cau_hinh_tra_503_chu_khong_phai_501(
        self, client: AsyncClient, db_session
    ):
        """Thiếu env là lỗi vận hành, khác hẳn "chưa làm tính năng" — hai thứ
        này cần hai hành động khác nhau nên không được trả cùng mã."""
        token = await _onboard(client, email="conn0003@havi.vn")
        _override(client, db_session, configured=False)

        response = await client.post(
            "/connections/facebook/start", headers=_headers(token)
        )

        assert response.status_code == 503, response.text


class TestCallback:
    async def test_callback_redirect_ve_app_khi_thanh_cong(
        self, client: AsyncClient, db_session
    ):
        """Callback là điều hướng trình duyệt — trả JSON ở đây thì chủ tiệm
        nhìn thấy một trang chữ thô sau khi bấm cấp quyền."""
        token = await _onboard(client, email="conn0004@havi.vn")
        _override(client, db_session)
        start = await client.post("/connections/facebook/start", headers=_headers(token))
        state = start.json()["state"]

        response = await client.get(
            "/connections/facebook/callback",
            params={"code": "code-tu-facebook", "state": state},
        )

        assert response.status_code == 302, response.text
        location = response.headers["location"]
        assert "ket_noi=ok" in location
        # Token không bao giờ được nằm trên URL — nó sẽ vào lịch sử trình duyệt.
        assert PAGE_TOKEN not in location

    async def test_nguoi_dung_bam_huy_khong_bi_422(self, client: AsyncClient, db_session):
        """Facebook gọi lại đúng URL này với `error=access_denied` và KHÔNG có
        `code`. Khai `code` bắt buộc thì FastAPI trả 422 và chủ tiệm mắc kẹt."""
        _override(client, db_session)

        response = await client.get(
            "/connections/facebook/callback",
            params={"error": "access_denied", "error_description": "Người dùng đã huỷ"},
        )

        assert response.status_code == 302, response.text
        assert "ket_noi=loi" in response.headers["location"]

    async def test_state_hong_van_redirect_kem_ly_do(
        self, client: AsyncClient, db_session
    ):
        _override(client, db_session)

        response = await client.get(
            "/connections/facebook/callback",
            params={"code": "code", "state": "state-bia-dat"},
        )

        assert response.status_code == 302
        assert "ket_noi=loi" in response.headers["location"]
        assert "ly_do=" in response.headers["location"]

    async def test_callback_khong_lot_vao_openapi(self, client: AsyncClient):
        """Callback không phải endpoint frontend gọi — để nó khỏi sinh ra
        client TypeScript mà không ai dùng."""
        schema = (await client.get("/openapi.json")).json()
        assert "/connections/{platform}/callback" not in schema["paths"]


class TestDuongVeSauCallback:
    """Nối kênh từ đâu thì quay về đó.

    Trước đây callback luôn redirect `/onboarding`, nên chủ tiệm dùng app hàng
    tháng bấm "Nối lại" ở Cài đặt xong bị đá vào wizard onboarding — một luồng
    họ đã làm xong từ lâu.
    """

    async def _state(self, client: AsyncClient, token: dict, tro_ve: str | None) -> str:
        params = {"tro_ve": tro_ve} if tro_ve else None
        start = await client.post(
            "/connections/facebook/start", params=params, headers=_headers(token)
        )
        assert start.status_code == 200, start.text
        return start.json()["state"]

    async def test_noi_tu_cai_dat_thi_quay_ve_cai_dat(
        self, client: AsyncClient, db_session
    ):
        token = await _onboard(client, email="conn0020@havi.vn")
        _override(client, db_session)
        state = await self._state(client, token, "settings")

        response = await client.get(
            "/connections/facebook/callback",
            params={"code": "code-tu-facebook", "state": state},
        )

        location = response.headers["location"]
        assert "/cai-dat?ket_noi=ok" in location
        assert "/onboarding" not in location

    async def test_noi_tu_onboarding_thi_quay_ve_onboarding(
        self, client: AsyncClient, db_session
    ):
        token = await _onboard(client, email="conn0021@havi.vn")
        _override(client, db_session)
        state = await self._state(client, token, "onboarding")

        response = await client.get(
            "/connections/facebook/callback",
            params={"code": "code-tu-facebook", "state": state},
        )

        assert "/onboarding?ket_noi=ok" in response.headers["location"]

    async def test_khong_khai_tro_ve_thi_mac_dinh_onboarding(
        self, client: AsyncClient, db_session
    ):
        """Giữ hành vi cũ cho mọi caller chưa truyền tham số này."""
        token = await _onboard(client, email="conn0022@havi.vn")
        _override(client, db_session)
        state = await self._state(client, token, None)

        response = await client.get(
            "/connections/facebook/callback",
            params={"code": "code-tu-facebook", "state": state},
        )

        assert "/onboarding?ket_noi=ok" in response.headers["location"]

    async def test_loi_cung_quay_ve_dung_trang(self, client: AsyncClient, db_session):
        """Báo lỗi xong vẫn phải đưa chủ tiệm về đúng nơi họ bấm — báo lỗi ở một
        trang họ không mở là mất dấu hoàn toàn."""
        token = await _onboard(client, email="conn0023@havi.vn")
        _override(client, db_session)
        state = await self._state(client, token, "settings")

        # Thiếu `code` = một lỗi thật (Facebook trả về thiếu tham số).
        response = await client.get(
            "/connections/facebook/callback", params={"state": state}
        )

        location = response.headers["location"]
        assert "/cai-dat?ket_noi=loi" in location

    async def test_tro_ve_gia_mao_bi_chan_o_422(self, client: AsyncClient, db_session):
        """`tro_ve` là enum nên URL lạ bị chặn ngay, không lọt tới state."""
        token = await _onboard(client, email="conn0024@havi.vn")
        _override(client, db_session)

        response = await client.post(
            "/connections/facebook/start",
            params={"tro_ve": "https://ke-tan-cong.example.com"},
            headers=_headers(token),
        )

        assert response.status_code == 422, response.text

    async def test_state_bi_sua_khong_doi_duoc_duong_ve(
        self, client: AsyncClient, db_session
    ):
        """Chốt chặn cuối cho open redirect: kể cả khi ai đó dựng được state
        mang `ret` là một URL đầy đủ, callback vẫn chỉ ghép đường trong
        allow-list — không bao giờ redirect ra ngoài domain Havi."""
        import jwt

        from core.config import get_settings
        from core.enums import Platform
        from core.oauth_state import _STATE_AUDIENCE  # noqa: PLC2701

        _override(client, db_session)
        settings = get_settings()
        # State ký bằng đúng khoá của hệ thống, nhưng `ret` là URL của kẻ tấn công.
        forged = jwt.encode(
            {
                "aud": _STATE_AUDIENCE,
                "ws": "00000000-0000-0000-0000-000000000001",
                "sub": "00000000-0000-0000-0000-000000000002",
                "plt": Platform.FACEBOOK.value,
                "ret": "https://ke-tan-cong.example.com",
                "exp": 9999999999,
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        response = await client.get(
            "/connections/facebook/callback",
            params={"code": "code", "state": forged},
        )

        location = response.headers["location"]
        assert "ke-tan-cong.example.com" not in location
        assert location.startswith(settings.web_base_url)


class TestListAndDisconnect:
    async def test_list_chi_thay_ket_noi_cua_workspace_minh(
        self, client: AsyncClient, db_session
    ):
        token_a = await _onboard(client, email="conn0005@havi.vn")
        token_b = await _onboard(client, email="conn0006@havi.vn")
        _override(client, db_session)

        start = await client.post(
            "/connections/facebook/start", headers=_headers(token_a)
        )
        await client.get(
            "/connections/facebook/callback",
            params={"code": "code", "state": start.json()["state"]},
        )

        list_a = await client.get("/connections", headers=_headers(token_a))
        list_b = await client.get("/connections", headers=_headers(token_b))

        assert [c["platform"] for c in list_a.json()] == ["facebook"]
        assert list_b.json() == [], "tiệm khác không được thấy kết nối này"

    async def test_response_khong_bao_gio_chua_token(
        self, client: AsyncClient, db_session
    ):
        token = await _onboard(client, email="conn0007@havi.vn")
        _override(client, db_session)
        start = await client.post("/connections/facebook/start", headers=_headers(token))
        await client.get(
            "/connections/facebook/callback",
            params={"code": "code", "state": start.json()["state"]},
        )

        response = await client.get("/connections", headers=_headers(token))

        assert PAGE_TOKEN not in response.text
        assert "access_token" not in response.text

    async def test_ngat_ket_noi_roi_list_rong(self, client: AsyncClient, db_session):
        token = await _onboard(client, email="conn0008@havi.vn")
        _override(client, db_session)
        start = await client.post("/connections/facebook/start", headers=_headers(token))
        await client.get(
            "/connections/facebook/callback",
            params={"code": "code", "state": start.json()["state"]},
        )

        deleted = await client.delete("/connections/facebook", headers=_headers(token))

        assert deleted.status_code == 204, deleted.text
        assert (await client.get("/connections", headers=_headers(token))).json() == []

    async def test_ngat_kenh_chua_noi_tra_404(self, client: AsyncClient, db_session):
        token = await _onboard(client, email="conn0009@havi.vn")
        _override(client, db_session)

        response = await client.delete("/connections/facebook", headers=_headers(token))

        assert response.status_code == 404, response.text
