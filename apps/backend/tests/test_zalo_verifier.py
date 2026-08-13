"""Route xác minh domain của Zalo — không được biến thành lỗ đọc file.

Bản đầu tiên của handler này ghép `{rest:path}` của request vào `os.path.join`
rồi trả `FileResponse`. Nghĩa là một request có `../` đọc được `.env` ở gốc repo:
JWT secret, khoá mã hoá token nền tảng, và toàn bộ API key provider. Test ở đây
khoá lại hình dạng an toàn: so khớp tuyệt đối, nội dung dựng sẵn, không chạm
filesystem.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import create_app
from core.config import get_settings

SUFFIX = "AbC123.html"
TOKEN = "test-zalo-token"


@pytest.fixture
def verifier_client(monkeypatch):
    monkeypatch.setenv("HAVI_ZALO_VERIFIER_SUFFIX", SUFFIX)
    monkeypatch.setenv("HAVI_ZALO_SITE_VERIFICATION", TOKEN)
    get_settings.cache_clear()
    app = create_app()
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_serves_verifier_for_exact_suffix(verifier_client):
    async with verifier_client as client:
        response = await client.get(f"/zalo_verifier{SUFFIX}")

    assert response.status_code == 200
    assert response.text == f"zalo-platform-site-verification={TOKEN}"


@pytest.mark.asyncio
async def test_rejects_any_other_suffix(verifier_client):
    async with verifier_client as client:
        response = await client.get("/zalo_verifierWrong.html")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/zalo_verifier/../../../.env",
        "/zalo_verifier%2F..%2F..%2F..%2F.env",
        "/zalo_verifier../.env",
        "/zalo_verifier/../../apps/backend/.env",
    ],
)
@pytest.mark.asyncio
async def test_traversal_attempts_never_return_file_contents(verifier_client, path):
    async with verifier_client as client:
        response = await client.get(path)

    assert response.status_code == 404
    assert "HAVI_JWT_SECRET" not in response.text
    assert "TOKEN_ENCRYPTION_KEY" not in response.text


@pytest.mark.asyncio
async def test_verifier_disabled_when_unconfigured(monkeypatch):
    monkeypatch.delenv("HAVI_ZALO_VERIFIER_SUFFIX", raising=False)
    get_settings.cache_clear()
    app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/zalo_verifier{SUFFIX}")

    get_settings.cache_clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_root_omits_meta_tag_when_unconfigured(monkeypatch):
    monkeypatch.delenv("HAVI_ZALO_SITE_VERIFICATION", raising=False)
    get_settings.cache_clear()
    app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    get_settings.cache_clear()
    assert response.status_code == 200
    assert "zalo-platform-site-verification" not in response.text
