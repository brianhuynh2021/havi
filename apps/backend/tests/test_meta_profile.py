"""Tra tên khách qua Graph: lấy được thì dùng, hỏng thì im lặng lùi về nhãn cũ.

Giá trị của module này nằm gần như trọn ở các nhánh *thất bại*. Tra được tên chỉ
làm inbox dễ đọc hơn; tra hỏng mà ném lỗi lên trên thì tin nhắn của khách không
vào được inbox — hỏng một thứ quan trọng hơn hẳn thứ đang cố làm cho đẹp. Nên
mỗi kiểu hỏng của Graph đều có một test riêng ở đây, và tất cả cùng kỳ vọng một
điều: trả `None`, không raise.
"""

import httpx
import pytest

from adapters.meta_profile import fetch_sender_name

pytestmark = pytest.mark.anyio

PSID = "27753642964332310"
PAGE_TOKEN = "EAAG-page-token-bi-mat"


def _client_factory(monkeypatch, handler) -> list[httpx.Request]:
    """Ép AsyncClient trong module dùng MockTransport, ghi lại request đã gửi."""
    seen: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    original = httpx.AsyncClient
    transport = httpx.MockTransport(recording)

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    import adapters.meta_profile as module

    monkeypatch.setattr(module.httpx, "AsyncClient", factory)
    return seen


class TestLayDuocTen:
    async def test_tra_ve_ten_that(self, monkeypatch):
        _client_factory(monkeypatch, lambda r: httpx.Response(200, json={"name": "Nguyễn Huỳnh"}))

        name = await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN)

        assert name == "Nguyễn Huỳnh"

    async def test_cat_khoang_trang_thua(self, monkeypatch):
        _client_factory(monkeypatch, lambda r: httpx.Response(200, json={"name": "  Trần Bình  "}))

        assert await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN) == "Trần Bình"

    async def test_token_di_o_header_khong_o_query(self, monkeypatch):
        """Query string bị ghi nguyên vào access log của mọi proxy trên đường."""
        seen = _client_factory(monkeypatch, lambda r: httpx.Response(200, json={"name": "A"}))

        await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN)

        request = seen[0]
        assert request.headers["Authorization"] == f"Bearer {PAGE_TOKEN}"
        assert PAGE_TOKEN not in str(request.url)
        assert "access_token" not in request.url.params
        assert PSID in request.url.path


class TestHongThiLuiVeNhanCu:
    """Mọi kiểu hỏng đều phải trả None — không kiểu nào được ném lỗi lên trên."""

    async def test_graph_tu_choi_quyen(self, monkeypatch):
        _client_factory(
            monkeypatch,
            lambda r: httpx.Response(403, json={"error": {"message": "khong du quyen"}}),
        )

        assert await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN) is None

    async def test_graph_loi_server(self, monkeypatch):
        _client_factory(monkeypatch, lambda r: httpx.Response(500, json={}))

        assert await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN) is None

    async def test_timeout(self, monkeypatch):
        def timeout(request):
            raise httpx.TimeoutException("qua han", request=request)

        _client_factory(monkeypatch, timeout)

        assert await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN) is None

    async def test_mat_ket_noi(self, monkeypatch):
        def broken(request):
            raise httpx.ConnectError("khong noi duoc", request=request)

        _client_factory(monkeypatch, broken)

        assert await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN) is None

    async def test_body_khong_phai_json(self, monkeypatch):
        _client_factory(monkeypatch, lambda r: httpx.Response(200, text="<html>loi</html>"))

        assert await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN) is None

    async def test_thieu_field_name(self, monkeypatch):
        _client_factory(monkeypatch, lambda r: httpx.Response(200, json={"id": PSID}))

        assert await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN) is None

    async def test_ten_rong(self, monkeypatch):
        _client_factory(monkeypatch, lambda r: httpx.Response(200, json={"name": "   "}))

        assert await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN) is None

    async def test_ten_khong_phai_chuoi(self, monkeypatch):
        _client_factory(monkeypatch, lambda r: httpx.Response(200, json={"name": 12345}))

        assert await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN) is None


class TestKhongLoToken:
    async def test_log_canh_bao_khong_mang_token(self, monkeypatch, caplog):
        """Đường lộ token dễ nhất không phải là hack mà là một dòng log."""
        _client_factory(monkeypatch, lambda r: httpx.Response(403, json={"error": {"x": 1}}))

        with caplog.at_level("WARNING"):
            await fetch_sender_name(psid=PSID, page_token=PAGE_TOKEN)

        assert caplog.text, "phải có log cảnh báo để còn chẩn đoán được"
        assert PAGE_TOKEN not in caplog.text
