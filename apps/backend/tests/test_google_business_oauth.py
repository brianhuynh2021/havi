"""Unit test suite cho GoogleBusinessOAuthClient."""

import pytest

from adapters.oauth.google_business import GoogleBusinessOAuthClient
from core.config import Settings
from core.enums import Platform


def test_google_business_oauth_client_properties():
    settings = Settings(
        google_client_id="test_google_id",
        google_client_secret="test_google_secret",
        env="local",
    )
    client = GoogleBusinessOAuthClient(settings)
    assert client.platform == Platform.GOOGLE_BUSINESS
    assert client.is_configured is True

    url = client.authorization_url(state="test_state_123")
    assert "https://accounts.google.com/o/oauth2/v2/auth" in url
    assert "business.manage" in url
    assert "test_state_123" in url


@pytest.mark.asyncio
async def test_google_business_oauth_client_mock_exchange():
    settings = Settings(
        google_client_id="",
        google_client_secret="",
        use_fake_publisher=True,
        env="local",
    )
    client = GoogleBusinessOAuthClient(settings)
    assert client.is_configured is True

    account = await client.exchange_code(code="mock_code")
    assert "locations/" in account.external_account_id
    assert account.account_name is not None
    assert account.access_token == "mock_google_business_access_token"


class TestPhanGiaiDiaDiemThat:
    """Không được bịa location ID từ danh tính người dùng Google.

    Bug thật: `exchange_code` gọi `userinfo`, lấy `id` của **người dùng** rồi
    gắn `locations/` vào trước::

        locations/117064704841566717018

    Kết nối lưu là CONNECTED, giao diện báo đã nối, và bài đăng chết ở
    dead-letter với một trang HTML 404 của Google. Hai job trong dead-letter thật
    đến từ đúng chỗ này.
    """

    @staticmethod
    def _client(handler):
        """Client thật, nhưng mọi request HTTP đi qua `handler` thay vì ra mạng."""
        import httpx

        settings = Settings(
            google_client_id="id",
            google_client_secret="secret",
            env="local",
        )
        oauth = GoogleBusinessOAuthClient(settings)
        transport = httpx.MockTransport(handler)

        real_init = httpx.AsyncClient.__init__

        def patched(self, *args, **kwargs):
            kwargs["transport"] = transport
            real_init(self, *args, **kwargs)

        return oauth, patched, real_init

    @pytest.mark.asyncio
    async def test_luu_duong_dan_day_du_accounts_va_locations(self, monkeypatch):
        """`localPosts` cần `accounts/{a}/locations/{l}` — thiếu nửa đầu là 404."""
        import httpx

        def handler(request: httpx.Request) -> httpx.Response:
            if "oauth2.googleapis.com" in request.url.host:
                return httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
            if "accountmanagement" in request.url.host:
                return httpx.Response(200, json={"accounts": [{"name": "accounts/111"}]})
            return httpx.Response(
                200,
                json={"locations": [{"name": "locations/222", "title": "Spa An Nhiên"}]},
            )

        oauth, patched, _ = self._client(handler)
        monkeypatch.setattr(httpx.AsyncClient, "__init__", patched)

        account = await oauth.exchange_code(code="real_code")

        assert account.external_account_id == "accounts/111/locations/222"
        assert account.account_name == "Spa An Nhiên"

    @pytest.mark.asyncio
    async def test_khong_co_dia_diem_thi_hong_ngay_luc_noi(self, monkeypatch):
        """Thà không nối được, còn hơn nối xong rồi hỏng ở một bài đăng ba ngày sau."""
        import httpx

        from adapters.oauth.base import OAuthPermanentError

        def handler(request: httpx.Request) -> httpx.Response:
            if "oauth2.googleapis.com" in request.url.host:
                return httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
            return httpx.Response(200, json={})

        oauth, patched, _ = self._client(handler)
        monkeypatch.setattr(httpx.AsyncClient, "__init__", patched)

        with pytest.raises(OAuthPermanentError) as err:
            await oauth.exchange_code(code="real_code")

        assert "hồ sơ doanh nghiệp" in str(err.value)

    @pytest.mark.asyncio
    async def test_403_noi_thang_la_chua_duoc_duyet_han_muc(self, monkeypatch):
        """Mặc định dự án Google Cloud có quota Business Profile bằng 0.

        Để nguyên "HTTP 403" thì người dùng đi kiểm tra lại mật khẩu Google —
        sai chỗ hoàn toàn.
        """
        import httpx

        from adapters.oauth.base import OAuthPermanentError

        def handler(request: httpx.Request) -> httpx.Response:
            if "oauth2.googleapis.com" in request.url.host:
                return httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
            return httpx.Response(403, json={"error": {"message": "denied"}})

        oauth, patched, _ = self._client(handler)
        monkeypatch.setattr(httpx.AsyncClient, "__init__", patched)

        with pytest.raises(OAuthPermanentError) as err:
            await oauth.exchange_code(code="real_code")

        assert "hạn mức" in str(err.value)

    @pytest.mark.asyncio
    async def test_google_tra_html_thi_khong_nhet_ca_trang_vao_thong_bao(self, monkeypatch):
        """Dead-letter thật chứa nguyên `<!DOCTYPE html><html lang=en>...`.

        HTML nghĩa là sai địa chỉ API, không phải sai dữ liệu — và một trang web
        dán vào ô thông báo lỗi thì không ai đọc được gì.
        """
        import httpx

        from adapters.oauth.base import OAuthPermanentError

        def handler(request: httpx.Request) -> httpx.Response:
            if "oauth2.googleapis.com" in request.url.host:
                return httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
            return httpx.Response(404, text="<!DOCTYPE html><html lang=en><title>Error 404</title>")

        oauth, patched, _ = self._client(handler)
        monkeypatch.setattr(httpx.AsyncClient, "__init__", patched)

        with pytest.raises(OAuthPermanentError) as err:
            await oauth.exchange_code(code="real_code")

        assert "<!DOCTYPE" not in str(err.value)
