"""Đường dẫn pháp lý phải tải được từ Internet, nếu không Meta chặn cả OAuth.

Meta kiểm Privacy Policy URL trước khi cho OAuth dialog chạy. URL hỏng thì
**mọi** lần nối kênh trả "Sorry, something went wrong" — không nói lý do, và
trông hệt lỗi thiếu quyền nên rất tốn thời gian truy.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client(monkeypatch):
    def fake_get(self, url, **kwargs):
        del kwargs
        if url.endswith(("/privacy", "/terms", "/data-deletion")):
            return httpx.Response(200, text="<html><body>Nội dung trang</body></html>")
        return httpx.Response(404, text="not found")

    monkeypatch.setattr(httpx.AsyncClient, "get", _as_async(fake_get))
    return TestClient(create_app())


def _as_async(fn):
    async def wrapper(self, url, **kwargs):
        return fn(self, url, **kwargs)

    return wrapper


@pytest.mark.parametrize("slug", ["bao-mat", "dieu-khoan", "xoa-du-lieu"])
def test_trang_phap_ly_tra_noi_dung_that(client, slug):
    response = client.get(f"/{slug}", follow_redirects=False)

    # 200 kèm nội dung, không phải 302 sang localhost: Meta đứng ngoài Internet
    # nên redirect tới `http://localhost:3000` sẽ dẫn nó tới một URL chết.
    assert response.status_code == 200
    assert "Nội dung trang" in response.text


def test_duong_dan_la_van_404(client):
    assert client.get("/khong-co-trang-nay").status_code == 404


def test_khong_nuot_route_san_co(client):
    """Từng khai `/{slug}` catch-all và nó ăn mất `/zalo_verifier{suffix}`."""
    assert client.get("/health").status_code == 200
    # zalo_verifier chưa cấu hình suffix nên 404 — nhưng phải là 404 của chính
    # nó, không phải bị route pháp lý nuốt mất.
    assert client.get("/zalo_verifier_bat_ky").status_code == 404


def test_web_chet_thi_bao_503_chu_khong_tra_trang_rong(monkeypatch):
    """Trang trắng "hợp lệ" sẽ lọt vòng kiểm của Meta rồi hỏng ở chỗ khó truy hơn."""

    async def boom(self, url, **kwargs):
        del url, kwargs
        raise httpx.ConnectError("web chưa chạy")

    monkeypatch.setattr(httpx.AsyncClient, "get", boom)
    client = TestClient(create_app(), raise_server_exceptions=False)

    assert client.get("/bao-mat").status_code == 503
