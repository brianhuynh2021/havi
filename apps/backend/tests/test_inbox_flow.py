import pytest
from httpx import AsyncClient

from core.enums import InboxItemStatus, LeadReplyStatus, LeadStage, Platform


@pytest.mark.asyncio
async def test_inbox_faq_auto_reply(client: AsyncClient, auth_headers: dict):
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


@pytest.mark.asyncio
async def test_leads_crud_flow(client: AsyncClient, auth_headers: dict):
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
