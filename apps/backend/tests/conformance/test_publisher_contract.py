"""Channel Adapter Conformance Suite — Bộ test tuân thủ cho mọi publisher adapter.

Theo COMMERCIAL_READINESS_PROMPT §1.1:
Một kênh chỉ được coi là LIVE khi adapter của nó vượt qua cùng một bộ test tuân thủ như Facebook.
Adapter TikTok/YouTube/Zalo/Google hiện có được phép skip có ghi lý do rõ ràng.
"""

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.publishers.facebook import FacebookPublisher
from core.config import Settings
from core.enums import Channel, Platform, PublishFailureKind
from domain.policies.connection_capabilities import Capability, capabilities_for, has_capability
from domain.ports.publisher import (
    AmbiguousPublishError,
    AuthPermissionError,
    PublishError,
    PublishRequest,
    PublishResult,
    TemporaryPublishError,
    ValidationPublishError,
)

ALL_CHANNELS = [
    Channel.FACEBOOK_PAGE,
    Channel.REELS,
    Channel.TIKTOK,
    Channel.YOUTUBE,
    Channel.GOOGLE_BUSINESS,
    Channel.ZALO_OA,
]


def _skip_if_unsupported(channel: Channel) -> None:
    if channel in (Channel.YOUTUBE, Channel.GOOGLE_BUSINESS, Channel.ZALO_OA):
        pytest.skip(f"{channel.value} conformance validation is scheduled for Phase 3 / Phase 4")


@pytest.mark.parametrize("channel", ALL_CHANNELS)
def test_capabilities_for_platform_matches(channel: Channel):
    """1. capabilities_for(platform) khai đúng, không bị assume everything vô căn cứ."""
    platform_map = {
        Channel.FACEBOOK_PAGE: Platform.FACEBOOK,
        Channel.REELS: Platform.FACEBOOK,
        Channel.TIKTOK: Platform.TIKTOK,
        Channel.YOUTUBE: Platform.YOUTUBE,
        Channel.GOOGLE_BUSINESS: Platform.GOOGLE_BUSINESS,
        Channel.ZALO_OA: Platform.ZALO_OA,
    }
    platform = platform_map[channel]
    caps = capabilities_for(platform, granted_scopes=None)
    assert isinstance(caps, frozenset)

    if platform is Platform.FACEBOOK:
        assert Capability.PUBLISH_POST in caps
        assert Capability.REPLY_COMMENT in caps
        assert Capability.REPLY_MESSAGE in caps
        assert Capability.RECEIVE_INBOX in caps
    elif platform is Platform.TIKTOK:
        assert Capability.PUBLISH_POST in caps
        assert Capability.REPLY_MESSAGE not in caps
        assert Capability.REPLY_COMMENT not in caps
        assert Capability.RECEIVE_INBOX not in caps
    elif platform is Platform.YOUTUBE:
        assert Capability.PUBLISH_POST in caps
        assert Capability.REPLY_MESSAGE not in caps


@pytest.mark.parametrize("channel", ALL_CHANNELS)
@pytest.mark.asyncio
async def test_ambiguous_outcome_when_2xx_has_no_external_id(channel: Channel, monkeypatch):
    """2. Provider trả 2xx nhưng không có external id hoặc đứt sau khi đã cấp id -> AmbiguousPublishError."""
    _skip_if_unsupported(channel)

    if channel is Channel.TIKTOK:
        from adapters.publishers.tiktok import TikTokPublisher

        def _tiktok_handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {}}, request=req)

        transport = httpx.MockTransport(_tiktok_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            pub = TikTokPublisher(client=client)
            with pytest.raises(AmbiguousPublishError):
                await pub.publish(
                    PublishRequest(text="TikTok video", media_urls=["https://havi.vn/clip.mp4"]),
                    access_token="mock_tok",
                )
        return

    if channel is Channel.REELS:
        def _reels_handler(req: httpx.Request) -> httpx.Response:
            if "video_reels" in str(req.url):
                return httpx.Response(200, json={"video_id": "vid_123", "upload_url": "https://rupload.facebook.com/x"}, request=req)
            if "rupload" in str(req.url):
                return httpx.Response(500, json={"error": "upload dropped"}, request=req)
            return httpx.Response(200, json={"success": True}, request=req)

        transport = httpx.MockTransport(_reels_handler)
    else:
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"success": True}, request=req)
        )

    _orig_client = httpx.AsyncClient
    monkeypatch.setattr(
        "adapters.publishers.facebook.httpx.AsyncClient",
        lambda *args, **kwargs: _orig_client(transport=transport),
    )

    settings = Settings(facebook_client_id="x", facebook_client_secret="y")
    pub = FacebookPublisher(settings)

    with pytest.raises(AmbiguousPublishError):
        req = PublishRequest(
            text="Test post",
            external_account_id="page_123",
            channel=channel,
            media_urls=["https://havi.vn/sample.mp4"] if channel is Channel.REELS else [],
        )
        await pub.publish(req, access_token="mock_token")


@pytest.mark.parametrize("channel", ALL_CHANNELS)
@pytest.mark.asyncio
async def test_temporary_error_classification_for_rate_limits_and_5xx(channel: Channel):
    """3. Timeout / 5xx / 429 -> TemporaryPublishError để worker retry theo backoff."""
    _skip_if_unsupported(channel)

    if channel is Channel.TIKTOK:
        from adapters.publishers.tiktok import TikTokPublisher

        for status in (429, 500, 503):
            transport = httpx.MockTransport(lambda req, s=status: httpx.Response(s, json={"error": "rate limit"}, request=req))
            async with httpx.AsyncClient(transport=transport) as client:
                pub = TikTokPublisher(client=client)
                with pytest.raises(TemporaryPublishError):
                    await pub.publish(
                        PublishRequest(text="vid", media_urls=["https://havi.vn/clip.mp4"]),
                        access_token="tok",
                    )
        return

    settings = Settings(facebook_client_id="x", facebook_client_secret="y")
    pub = FacebookPublisher(settings)

    # 429
    resp_429 = httpx.Response(429, json={"error": {"message": "Rate limit"}}, request=httpx.Request("POST", "https://x"))
    err = pub._classify_error(resp_429)
    assert isinstance(err, TemporaryPublishError)
    assert err.kind == PublishFailureKind.TEMPORARY

    # 503
    resp_503 = httpx.Response(503, json={"error": {"message": "Service unavailable"}}, request=httpx.Request("POST", "https://x"))
    err_503 = pub._classify_error(resp_503)
    assert isinstance(err_503, TemporaryPublishError)


@pytest.mark.parametrize("channel", ALL_CHANNELS)
@pytest.mark.asyncio
async def test_auth_error_classification(channel: Channel):
    """4. 401 / 403 / token revoked -> AuthPermissionError, không retry."""
    _skip_if_unsupported(channel)

    if channel is Channel.TIKTOK:
        from adapters.publishers.tiktok import TikTokPublisher

        # Missing token
        pub = TikTokPublisher()
        with pytest.raises(AuthPermissionError):
            await pub.publish(PublishRequest(text="vid", media_urls=["https://havi.vn/clip.mp4"]), access_token="")

        # 401 response
        transport = httpx.MockTransport(lambda req: httpx.Response(401, json={"error": {"message": "unauthorized"}}, request=req))
        async with httpx.AsyncClient(transport=transport) as client:
            pub2 = TikTokPublisher(client=client)
            with pytest.raises(AuthPermissionError):
                await pub2.publish(PublishRequest(text="vid", media_urls=["https://havi.vn/clip.mp4"]), access_token="invalid_tok")
        return

    settings = Settings(facebook_client_id="x", facebook_client_secret="y")
    pub = FacebookPublisher(settings)

    for code in (190, 200, 102, 10):
        resp = httpx.Response(400, json={"error": {"code": code, "message": "Auth error"}}, request=httpx.Request("POST", "https://x"))
        err = pub._classify_error(resp)
        assert isinstance(err, AuthPermissionError)
        assert err.kind == PublishFailureKind.AUTH_PERMISSION


@pytest.mark.parametrize("channel", ALL_CHANNELS)
@pytest.mark.asyncio
async def test_validation_permanent_error_classification(channel: Channel):
    """5. Lỗi nội dung bị từ chối -> ValidationPublishError, không retry."""
    _skip_if_unsupported(channel)

    if channel is Channel.TIKTOK:
        from adapters.publishers.tiktok import TikTokPublisher

        pub = TikTokPublisher()
        # Missing video url
        with pytest.raises(ValidationPublishError):
            await pub.publish(PublishRequest(text="No video", media_urls=[]), access_token="tok")

        # 400 rejection
        transport = httpx.MockTransport(lambda req: httpx.Response(400, json={"error": {"message": "Invalid aspect ratio"}}, request=req))
        async with httpx.AsyncClient(transport=transport) as client:
            pub2 = TikTokPublisher(client=client)
            with pytest.raises(ValidationPublishError):
                await pub2.publish(PublishRequest(text="vid", media_urls=["https://havi.vn/clip.mp4"]), access_token="tok")
        return

    settings = Settings(facebook_client_id="x", facebook_client_secret="y")
    pub = FacebookPublisher(settings)

    resp = httpx.Response(400, json={"error": {"code": 99999, "message": "Invalid format"}}, request=httpx.Request("POST", "https://x"))
    err = pub._classify_error(resp)
    assert isinstance(err, ValidationPublishError)
    assert err.kind == PublishFailureKind.VALIDATION_PERMANENT


@pytest.mark.parametrize("channel", ALL_CHANNELS)
def test_granted_scopes_verification(channel: Channel):
    """6. Kiểm tra granted_scopes của kênh."""
    _skip_if_unsupported(channel)

    if channel is Channel.TIKTOK:
        from adapters.oauth.tiktok import TIKTOK_SCOPES
        assert "video.upload" in TIKTOK_SCOPES
        assert "user.info.basic" in TIKTOK_SCOPES
        return

    from adapters.oauth.facebook import SCOPES
    assert "pages_manage_posts" in SCOPES
    assert "pages_read_engagement" in SCOPES


@pytest.mark.parametrize("channel", ALL_CHANNELS)
@pytest.mark.asyncio
async def test_reconciliation_support(channel: Channel):
    """7. Kênh có cơ chế reconciliation để giải phóng job pending_reconciliation."""
    _skip_if_unsupported(channel)

    if channel is Channel.TIKTOK:
        from adapters.publishers.tiktok import TikTokPublisher

        def _tiktok_status_handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "status": "PUBLISH_COMPLETE",
                        "publicaly_available_post_id": ["v_pub_tiktok_live_123"],
                    }
                },
                request=req,
            )

        transport = httpx.MockTransport(_tiktok_status_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            pub = TikTokPublisher(client=client)
            assert hasattr(pub, "verify_publish_status")
            assert hasattr(pub, "reconcile")
            outcome = await pub.reconcile(external_post_id="v_pub_123", access_token="tok")
            assert outcome.is_published
            assert outcome.external_post_id == "v_pub_tiktok_live_123"
        return

    settings = Settings(facebook_client_id="x", facebook_client_secret="y")
    pub = FacebookPublisher(settings)
    assert hasattr(pub, "verify_reel")
    assert hasattr(pub, "reconcile")
