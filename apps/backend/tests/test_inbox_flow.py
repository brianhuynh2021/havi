import pytest
from httpx import AsyncClient

from core.enums import LeadStage


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
async def test_inbox_faq_auto_reply(client: AsyncClient):
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

    # 3. Simulate inbound FAQ message -> auto reply
    sim_resp = await client.post(
        "/webhooks/dev/simulate",
        json={"content": "Giờ mở cửa", "author_name": "Khách A"},
        headers=auth_headers,
    )
    assert sim_resp.status_code == 200
    assert sim_resp.json()["status"] == "sent"

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
    assert reply_resp.json()["ai_suggested_reply"] is not None


@pytest.mark.asyncio
async def test_leads_crud_flow(client: AsyncClient):
    auth_headers = await _onboard(client, "mai.leads@havi.vn")

    # 1. Create a lead
    create_payload = {
        "name": "Chị Mai Q7",
        "phone": "0901234567",
        "source": "fanpage",
        "message": "Tư vấn gói gội đầu dưỡng sinh",
    }
    resp = await client.post("/leads", json=create_payload, headers=auth_headers)
    assert resp.status_code == 201
    lead_data = resp.json()
    assert lead_data["name"] == "Chị Mai Q7"
    assert lead_data["stage"] == LeadStage.NEW.value

    # 2. List leads
    resp = await client.get("/leads", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    # 3. Update lead stage & notes
    update_payload = {"stage": "qualified", "notes": "Khách thích hẹn 15:00 thứ Bảy"}
    resp = await client.patch(
        f"/leads/{lead_data['id']}", json=update_payload, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["stage"] == "qualified"
    assert resp.json()["notes"] == "Khách thích hẹn 15:00 thứ Bảy"
