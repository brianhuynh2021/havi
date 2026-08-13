"""Adapter Zalo OA: map lỗi OpenAPI Zalo v3 sang các ngoại lệ chuẩn của Havi.

Kiểm tra:
1. Đăng thành công với Zalo OA message paragraph API.
2. Token thiếu / hết hạn / bị thu hồi -> AuthPermissionError.
3. Lỗi rate limit 429 hoặc 5xx -> TemporaryPublishError.
4. Lỗi format / media không hợp lệ -> ValidationPublishError.
"""

import httpx
import pytest

from adapters.publishers.zalo import ZaloPublisher
from core.enums import Channel
from domain.ports.publisher import (
    AuthPermissionError,
    PublishRequest,
    TemporaryPublishError,
    ValidationPublishError,
)

pytestmark = pytest.mark.anyio


def _zalo_publisher(client: httpx.AsyncClient | None = None) -> ZaloPublisher:
    return ZaloPublisher(client=client)


class TestZaloPublisher:
    async def test_thieu_token_la_auth_error(self):
        pub = _zalo_publisher()
        with pytest.raises(AuthPermissionError, match="Missing Zalo OA access token"):
            await pub.publish(
                PublishRequest(text="Chào chị, tiệm gội đầu ưu đãi", external_account_id="zalo_123"),
                access_token="",
            )

    async def test_publish_thanh_cong(self):
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            assert request.url == "https://openapi.zalo.me/v3.0/oa/message/paragraph"
            assert request.headers.get("access_token") == "zalo_token_abc"
            return httpx.Response(
                200,
                json={"error": 0, "message": "Success", "data": {"message_id": "zalo_msg_999"}},
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        pub = _zalo_publisher(client=client)
        result = await pub.publish(
            PublishRequest(
                text="Ưu đãi gội đầu thảo dược thứ 7",
                external_account_id="zalo_123",
                media_urls=["https://storage.havi.vn/img.jpg"],
            ),
            access_token="zalo_token_abc",
        )
        assert result.external_post_id == "zalo_msg_999"

    async def test_token_het_han_401_la_auth_error(self):
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": -216, "message": "Access token expired"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        pub = _zalo_publisher(client=client)
        with pytest.raises(AuthPermissionError, match="expired or revoked"):
            await pub.publish(
                PublishRequest(text="Mô tả", external_account_id="zalo_123"),
                access_token="expired_token",
            )

    async def test_rate_limit_429_la_temporary_error(self):
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": -1, "message": "Rate limit exceeded"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        pub = _zalo_publisher(client=client)
        with pytest.raises(TemporaryPublishError, match="HTTP 429"):
            await pub.publish(
                PublishRequest(text="Mô tả", external_account_id="zalo_123"),
                access_token="zalo_token",
            )

    async def test_zalo_error_code_invalid_format_la_validation_error(self):
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"error": -204, "message": "Invalid parameters format"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        pub = _zalo_publisher(client=client)
        with pytest.raises(ValidationPublishError, match="Zalo Error -204"):
            await pub.publish(
                PublishRequest(text="Mô tả", external_account_id="zalo_123"),
                access_token="zalo_token",
            )
