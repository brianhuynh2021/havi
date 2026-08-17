"""Test cho FacebookReplyAdapter: gửi tin nhắn thật qua Graph API."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest

from adapters.publishers.facebook_reply import FacebookReplyAdapter
from core.enums import ConnectionStatus, Platform
from domain.models.connection import PlatformConnection
from domain.ports.reply_publisher import ReplyError, ReplyRequest

pytestmark = pytest.mark.anyio


def _mock_connections(connection: PlatformConnection | None = None) -> MagicMock:
    repo = MagicMock()
    repo.get = AsyncMock(return_value=connection)
    repo.read_access_token = MagicMock(return_value="EAAG_test_page_access_token")
    return repo


async def test_send_reply_success(monkeypatch):
    workspace_id = uuid4()
    conn = PlatformConnection(
        workspace_id=workspace_id,
        platform=Platform.FACEBOOK,
        external_account_id="page_123456",
        status=ConnectionStatus.CONNECTED,
        access_token_encrypted="encrypted",
    )
    repo = _mock_connections(conn)
    adapter = FacebookReplyAdapter(repo)

    async def mock_post(self, url, json=None, headers=None):
        assert "page_123456/messages" in url
        assert json["recipient"]["id"] == "user_msg_999"
        assert json["message"]["text"] == "Dạ Havi xin chào bạn!"
        assert headers["Authorization"] == "Bearer EAAG_test_page_access_token"
        return httpx.Response(
            200,
            json={"recipient_id": "user_msg_999", "message_id": "m_mid_test_123"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await adapter.send_reply(
        ReplyRequest(
            workspace_id=workspace_id,
            platform=Platform.FACEBOOK,
            text="Dạ Havi xin chào bạn!",
            recipient_id="user_msg_999",
        )
    )

    assert result.external_reply_id == "m_mid_test_123"
    assert result.sent_at is not None


async def test_send_reply_no_connection():
    repo = _mock_connections(None)
    adapter = FacebookReplyAdapter(repo)

    with pytest.raises(ReplyError) as exc:
        await adapter.send_reply(
            ReplyRequest(
                workspace_id=uuid4(),
                platform=Platform.FACEBOOK,
                text="Test",
                recipient_id="user_123",
            )
        )
    assert "Chưa kết nối Fanpage" in str(exc.value)


async def test_send_reply_meta_api_error(monkeypatch):
    workspace_id = uuid4()
    conn = PlatformConnection(
        workspace_id=workspace_id,
        platform=Platform.FACEBOOK,
        external_account_id="page_123456",
        status=ConnectionStatus.CONNECTED,
        access_token_encrypted="encrypted",
    )
    repo = _mock_connections(conn)
    adapter = FacebookReplyAdapter(repo)

    async def mock_post(self, url, json=None, headers=None):
        return httpx.Response(
            400,
            json={"error": {"code": 190, "message": "Invalid OAuth access token."}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    with pytest.raises(ReplyError) as exc:
        await adapter.send_reply(
            ReplyRequest(
                workspace_id=workspace_id,
                platform=Platform.FACEBOOK,
                text="Dạ chào bạn",
                recipient_id="user_123",
            )
        )
    assert "Meta Graph API error (190)" in str(exc.value)
