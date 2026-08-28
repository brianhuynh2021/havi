from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from application.services.inbox_service import InboxService
from core.enums import InboxItemStatus, Platform
from domain.models.inbox import InboxItem
from domain.ports.reply_publisher import ReplyError


async def _onboard(client: AsyncClient, email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up", json={"name": "Chị Mai", "email": email, "password": "matkhau123"}
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()

    headers = {"Authorization": f"Bearer {token_pair['access_token']}"}
    create = await client.post(
        "/workspaces",
        json={"name": "Tiệm Mai Q7", "industry": "spa"},
        headers=headers,
    )
    assert create.status_code == 201, create.text

    refreshed = await client.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {token_pair['refresh_token']}"},
    )
    assert refreshed.status_code == 200, refreshed.text
    new_access = refreshed.json()["access_token"]
    return {"Authorization": f"Bearer {new_access}"}


@pytest.mark.asyncio
async def test_inbox_faq_is_suggested_but_waits_for_human(client: AsyncClient):
    auth_headers = await _onboard(client, "mai.inbox@havi.vn")

    # 1. Update brand profile with approved FAQ
    faq_payload = {
        "faq": [
            {
                "question": "Giờ mở cửa",
                "answer": "Tiệm mở cửa từ 8:00 đến 21:00 hàng ngày ạ!",
                "approved": True,
            }
        ]
    }
    resp = await client.put("/brand-profile", json=faq_payload, headers=auth_headers)
    assert resp.status_code == 200

    # 2. Get initial inbox list
    resp = await client.get("/inbox", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    # 3. FAQ khớp chính xác vẫn chỉ là bản nháp chờ người thật bấm gửi.
    sim_resp = await client.post(
        "/webhooks/dev/simulate",
        json={"content": "Giờ mở cửa", "author_name": "Khách A"},
        headers=auth_headers,
    )
    assert sim_resp.status_code == 200
    assert sim_resp.json()["status"] == "drafted"
    faq_item_id = sim_resp.json()["id"]
    listing = await client.get("/inbox", headers=auth_headers)
    faq_item = next(item for item in listing.json()["items"] if item["id"] == faq_item_id)
    assert faq_item["ai_suggested_reply"] == "Tiệm mở cửa từ 8:00 đến 21:00 hàng ngày ạ!"

    # 4. Simulate inbound non-FAQ message -> drafted
    sim_resp2 = await client.post(
        "/webhooks/dev/simulate",
        json={"content": "Gửi cho mình bảng giá dịch vụ với", "author_name": "Khách B"},
        headers=auth_headers,
    )
    assert sim_resp2.status_code == 200
    assert sim_resp2.json()["status"] == "drafted"
    item_id = sim_resp2.json()["id"]

    # 5. Send reply via API
    reply_resp = await client.post(
        f"/inbox/{item_id}/reply",
        json={"text": "Dạ tiệm xin gửi chị bảng giá mới nhất ạ!"},
        headers=auth_headers,
    )
    assert reply_resp.status_code == 200
    assert reply_resp.json()["status"] == "sent"
    assert reply_resp.json()["sent_reply_text"] == "Dạ tiệm xin gửi chị bảng giá mới nhất ạ!"
    assert reply_resp.json()["replied_at"] is not None


@pytest.mark.asyncio
async def test_inbox_reply_error_handling(client: AsyncClient, monkeypatch):
    from adapters.publishers.fake_reply import FakeReplyPublisher
    from domain.ports.reply_publisher import ReplyError

    auth_headers = await _onboard(client, "mai.failtest@havi.vn")

    sim_resp = await client.post(
        "/webhooks/dev/simulate",
        json={"content": "Tư vấn giá liệu trình", "author_name": "Khách Test Lỗi"},
        headers=auth_headers,
    )
    assert sim_resp.status_code == 200
    item_id = sim_resp.json()["id"]

    async def mock_fail_send(*args, **kwargs):
        raise ReplyError(Platform.FACEBOOK, "Facebook Graph API token expired (code 190)")

    monkeypatch.setattr(FakeReplyPublisher, "send_reply", mock_fail_send)

    reply_resp = await client.post(
        f"/inbox/{item_id}/reply",
        json={"text": "Dạ tiệm xin chào bạn ạ!"},
        headers=auth_headers,
    )
    assert reply_resp.status_code == 502
    assert "Facebook Graph API token expired" in reply_resp.json()["detail"]

    # Verify status in database is now 'failed' (Zero False Success)
    inbox_list = await client.get("/inbox", headers=auth_headers)
    assert inbox_list.status_code == 200
    items = inbox_list.json()["items"]
    target_item = next(it for it in items if it["id"] == item_id)
    assert target_item["status"] == "failed"


@pytest.mark.asyncio
async def test_inbox_never_falls_back_to_fake_publisher():
    """Thiếu adapter thật phải thất bại rõ ràng, không được giả lập SENT."""
    workspace_id = uuid4()
    item = InboxItem(
        id=uuid4(),
        workspace_id=workspace_id,
        platform=Platform.ZALO_OA,
        content="Cho mình xin bảng giá",
        author_name="Khách Zalo",
        status=InboxItemStatus.DRAFTED,
    )
    inbox = AsyncMock()
    inbox.get.return_value = item
    inbox.update_status.return_value = item
    events = AsyncMock()
    service = InboxService(
        inbox=inbox,
        profiles=AsyncMock(),
        events=events,
        reply_publishers={},
    )

    with pytest.raises(ReplyError, match="Chưa cấu hình kênh"):
        await service.send_reply(
            workspace_id=workspace_id,
            item_id=item.id,
            text="Dạ đây là bảng giá ạ",
        )

    inbox.update_status.assert_awaited_once_with(
        item,
        status=InboxItemStatus.FAILED,
        reply_text="Dạ đây là bảng giá ạ",
    )
    events.record.assert_awaited_once()
