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
            oauth_clients={Platform.FACEBOOK: _StubOAuthClient(configured=configured)},
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
        """Zalo chưa có adapter — 501 để UI không hiện "đã nối" cho kênh fixture."""
        token = await _onboard(client, email="conn0002@havi.vn")
        _override(client, db_session)

        response = await client.post(
            "/connections/zalo_oa/start", headers=_headers(token)
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
