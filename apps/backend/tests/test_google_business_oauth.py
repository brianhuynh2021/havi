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
