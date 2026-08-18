"""Unit test suite for TikTok Publisher adapter and TikTok OAuth client.

Verifies:
1. TikTok publisher successful video post initiation payload and post ID return.
2. Error classification (AuthPermissionError, TemporaryPublishError, ValidationPublishError).
3. Missing token and missing media validation.
4. TikTok OAuth client URL generation and mock exchange.
"""

import httpx
import pytest

from adapters.oauth.tiktok import TikTokOAuthClient
from adapters.publishers.tiktok import TikTokPublisher
from core.config import Settings
from core.enums import Platform
from domain.ports.publisher import (
    AuthPermissionError,
    PublishRequest,
    TemporaryPublishError,
    ValidationPublishError,
)


@pytest.mark.asyncio
async def test_tiktok_publisher_missing_token():
    publisher = TikTokPublisher()
    req = PublishRequest(text="Video spa", media_urls=["https://example.com/video.mp4"])
    with pytest.raises(AuthPermissionError):
        await publisher.publish(req, access_token="")


@pytest.mark.asyncio
async def test_tiktok_publisher_missing_video():
    publisher = TikTokPublisher()
    req = PublishRequest(text="Video spa", media_urls=[])
    with pytest.raises(ValidationPublishError):
        await publisher.publish(req, access_token="valid_tiktok_token")


@pytest.mark.asyncio
async def test_tiktok_publisher_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer valid_tiktok_token"
        assert request.headers.get("X-Idempotency-Key") == "job_123"
        return httpx.Response(
            200,
            json={
                "data": {
                    "publish_id": "v_pub_tiktok_98765",
                },
                "error": {
                    "code": "ok",
                    "message": "",
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        publisher = TikTokPublisher(client=client)
        req = PublishRequest(
            text="Trải nghiệm dịch vụ chăm sóc da chuyên sâu tại Havi Spa",
            media_urls=["https://storage.havi.vn/videos/spa_intro.mp4"],
            idempotency_key="job_123",
        )
        res = await publisher.publish(req, access_token="valid_tiktok_token")
        assert res.external_post_id == "v_pub_tiktok_98765"


@pytest.mark.asyncio
async def test_tiktok_publisher_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        err_json = {"error": {"code": "access_token_invalid", "message": "Token expired"}}
        return httpx.Response(401, json=err_json)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        publisher = TikTokPublisher(client=client)
        req = PublishRequest(
            text="Video review",
            media_urls=["https://storage.havi.vn/video.mp4"],
        )
        with pytest.raises(AuthPermissionError):
            await publisher.publish(req, access_token="expired_token")


@pytest.mark.asyncio
async def test_tiktok_publisher_rate_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit exceeded"}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        publisher = TikTokPublisher(client=client)
        req = PublishRequest(
            text="Video",
            media_urls=["https://storage.havi.vn/video.mp4"],
        )
        with pytest.raises(TemporaryPublishError):
            await publisher.publish(req, access_token="valid_token")


@pytest.mark.asyncio
async def test_tiktok_oauth_client_mock_mode():
    settings = Settings(
        env="local",
        use_fake_publisher=True,
        tiktok_client_key="",
        tiktok_client_secret="",
    )
    oauth = TikTokOAuthClient(settings)
    assert oauth.platform == Platform.TIKTOK
    assert oauth.is_configured is True

    auth_url = oauth.authorization_url(state="test_state_123")
    assert "mock_tiktok_code" in auth_url
    assert "state=test_state_123" in auth_url

    account = await oauth.exchange_code("mock_tiktok_code")
    assert account.external_account_id == "tiktok_mock_user_123"
    assert account.access_token == "mock_tiktok_access_token"


@pytest.mark.asyncio
async def test_tiktok_oauth_client_real_url():
    settings = Settings(
        env="local",
        tiktok_client_key="test_key_123",
        tiktok_client_secret="test_secret_456",
        tiktok_redirect_uri="http://localhost:8000/connections/tiktok/callback",
    )
    oauth = TikTokOAuthClient(settings)
    auth_url = oauth.authorization_url(state="test_state_xyz")
    assert "client_key=test_key_123" in auth_url
    assert "scope=user.info.basic%2Cvideo.upload" in auth_url
    assert "state=test_state_xyz" in auth_url
    assert "code_challenge=" in auth_url
    assert "code_challenge_method=S256" in auth_url


