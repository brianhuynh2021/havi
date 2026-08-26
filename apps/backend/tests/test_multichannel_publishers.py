"""Unit test suite for Zalo OA and Google Business Profile publisher adapters.

Verifies:
1. Successful publishing payload formatting and external post ID return.
2. Error classification hierarchy (AuthPermissionError for 401/403,
   TemporaryPublishError for 429/5xx).
3. Missing access token handling.
"""

import httpx
import pytest

from adapters.publishers.google_business import GoogleBusinessPublisher
from adapters.publishers.zalo import ZaloPublisher
from domain.ports.publisher import (
    AuthPermissionError,
    PublishRequest,
    TemporaryPublishError,
)


@pytest.mark.asyncio
async def test_zalo_publisher_missing_token():
    publisher = ZaloPublisher()
    req = PublishRequest(text="Hello Zalo OA")
    with pytest.raises(AuthPermissionError):
        await publisher.publish(req, access_token="")


@pytest.mark.asyncio
async def test_zalo_publisher_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("access_token") == "valid_zalo_token"
        return httpx.Response(
            200,
            json={
                "error": 0,
                "message": "Success",
                "data": {"message_id": "zalo_12345"},
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        publisher = ZaloPublisher(client=client)
        req = PublishRequest(
            text="Special promotion at Havi Spa",
            media_urls=["https://example.com/photo.jpg"],
            external_account_id="oa_9988",
        )
        res = await publisher.publish(req, access_token="valid_zalo_token")
        assert res.external_post_id == "zalo_12345"


@pytest.mark.asyncio
async def test_zalo_publisher_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": -216, "message": "Access token expired"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        publisher = ZaloPublisher(client=client)
        req = PublishRequest(text="Promo post")
        with pytest.raises(AuthPermissionError):
            await publisher.publish(req, access_token="expired_token")


@pytest.mark.asyncio
async def test_google_business_publisher_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Bearer valid_google_token" in request.headers.get("Authorization", "")
        return httpx.Response(200, json={"name": "accounts/123/locations/456/localPosts/789"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        publisher = GoogleBusinessPublisher(client=client)
        req = PublishRequest(
            text="New organic coffee beans available at Havi Cafe!",
            media_urls=["https://example.com/coffee.jpg"],
            external_account_id="accounts/123/locations/456",
        )
        res = await publisher.publish(req, access_token="valid_google_token")
        assert res.external_post_id == "accounts/123/locations/456/localPosts/789"


@pytest.mark.asyncio
async def test_google_business_publisher_rate_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit exceeded"}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        publisher = GoogleBusinessPublisher(client=client)
        req = PublishRequest(
            text="Local post update",
            # Kênh đã nối luôn có đường dẫn địa điểm đầy đủ; thiếu nó là lỗi cấu hình,
            # không phải một ca cần test ở đây.
            external_account_id="accounts/111/locations/222",
        )
        with pytest.raises(TemporaryPublishError):
            await publisher.publish(req, access_token="valid_google_token")
