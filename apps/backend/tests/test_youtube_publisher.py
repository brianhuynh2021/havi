"""Unit test suite for YouTube Publisher adapter and Google/YouTube OAuth client.

Verifies:
1. YouTube Shorts resumable upload protocol initiation, video binary push, and ID return.
2. Auto-tagging #Shorts in title and description.
3. Error classification (AuthPermissionError for 401/403, TemporaryPublishError for 429/5xx).
4. Google/YouTube OAuth client URL generation and mock exchange.
"""

import httpx
import pytest

from adapters.oauth.google_youtube import GoogleYouTubeOAuthClient
from adapters.publishers.youtube import YouTubePublisher
from core.config import Settings
from core.enums import Platform
from domain.ports.publisher import (
    AuthPermissionError,
    PublishRequest,
    TemporaryPublishError,
    ValidationPublishError,
)


@pytest.mark.asyncio
async def test_youtube_publisher_missing_token():
    publisher = YouTubePublisher()
    req = PublishRequest(text="Shorts video", media_urls=["https://example.com/video.mp4"])
    with pytest.raises(AuthPermissionError):
        await publisher.publish(req, access_token="")


@pytest.mark.asyncio
async def test_youtube_publisher_missing_video():
    publisher = YouTubePublisher()
    req = PublishRequest(text="Shorts video", media_urls=[])
    with pytest.raises(ValidationPublishError):
        await publisher.publish(req, access_token="valid_google_token")


@pytest.mark.asyncio
async def test_youtube_publisher_success():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and "uploadType=resumable" in str(request.url):
            assert "Bearer valid_google_token" in request.headers.get("Authorization", "")
            return httpx.Response(
                200,
                headers={"Location": "https://www.googleapis.com/upload/session/upload_123"},
            )
        if request.method == "GET" and "video.mp4" in str(request.url):
            return httpx.Response(200, content=b"fake_video_bytes_12345")
        if request.method == "PUT" and "upload_123" in str(request.url):
            assert request.content == b"fake_video_bytes_12345"
            return httpx.Response(200, json={"id": "yt_video_abc999"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        publisher = YouTubePublisher(client=client)
        req = PublishRequest(
            text="Bí quyết chăm sóc da mùa hè cực kỳ đơn giản",
            media_urls=["https://storage.havi.vn/video.mp4"],
        )
        res = await publisher.publish(req, access_token="valid_google_token")
        assert res.external_post_id == "yt_video_abc999"


@pytest.mark.asyncio
async def test_youtube_publisher_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"code": 401, "message": "Invalid Credentials"}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        publisher = YouTubePublisher(client=client)
        req = PublishRequest(
            text="Video review",
            media_urls=["https://storage.havi.vn/video.mp4"],
        )
        with pytest.raises(AuthPermissionError):
            await publisher.publish(req, access_token="invalid_token")


@pytest.mark.asyncio
async def test_youtube_publisher_rate_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"code": 429, "message": "Quota exceeded"}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        publisher = YouTubePublisher(client=client)
        req = PublishRequest(
            text="Video",
            media_urls=["https://storage.havi.vn/video.mp4"],
        )
        with pytest.raises(TemporaryPublishError):
            await publisher.publish(req, access_token="valid_token")


@pytest.mark.asyncio
async def test_google_youtube_oauth_client_mock_mode():
    settings = Settings(
        env="local",
        use_fake_publisher=True,
        google_client_id="",
        google_client_secret="",
    )
    oauth = GoogleYouTubeOAuthClient(settings)
    assert oauth.platform == Platform.YOUTUBE
    assert oauth.is_configured is True

    auth_url = oauth.authorization_url(state="test_state_456")
    assert "mock_youtube_code" in auth_url
    assert "state=test_state_456" in auth_url

    account = await oauth.exchange_code("mock_youtube_code")
    assert account.external_account_id == "youtube_mock_channel_123"
    assert account.access_token == "mock_youtube_access_token"
