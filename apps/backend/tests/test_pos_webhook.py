"""Integration tests cho POS Webhook (Station 5 Closed-Loop Sales)."""

import pytest
from httpx import AsyncClient

from core.enums import LeadStage


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chị Lan Chủ Tiệm", "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()
    create = await client.post(
        "/workspaces",
        json={"name": "Tiệm Spa Mộc Lan", "industry": "spa"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert create.status_code == 201, create.text
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


@pytest.mark.asyncio
async def test_pos_webhook_ingests_new_order_and_creates_won_lead(client: AsyncClient):
    auth = await _onboard(client, email="lan.pos@example.com")
    workspace_id = auth["active_workspace_id"]

    # 1. Gửi đơn hàng từ POS
    res = await client.post(
        "/webhooks/pos",
        params={"workspace_id": workspace_id},
        json={
            "order_id": "HD-1001",
            "customer_name": "Nguyễn Thị Mai",
            "customer_phone": "0988 123 456",
            "amount_vnd": 650000,
            "source": "kiotviet",
            "items": ["Massage body đá nóng", "Gội đầu dưỡng sinh"],
        },
        headers=_headers(auth),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    assert body["customer_name"] == "Nguyễn Thị Mai"
    assert body["amount_vnd"] == 650000
    assert body["stage"] == LeadStage.WON.value

    # 2. Kiểm tra danh sách Leads trên workspace
    leads_res = await client.get("/leads", headers=_headers(auth))
    assert leads_res.status_code == 200
    leads = leads_res.json()["items"]
    assert len(leads) >= 1
    mai_lead = next(lead for lead in leads if lead["id"] == body["lead_id"])
    assert mai_lead["stage"] == LeadStage.WON.value
    assert "HD-1001" in (mai_lead["notes"] or "")
    assert "KIOTVIET" in (mai_lead["notes"] or "")

    # 3. Gửi lại cùng order_id -> Chống trùng (Idempotency)
    dup_res = await client.post(
        "/webhooks/pos",
        params={"workspace_id": workspace_id},
        json={
            "order_id": "HD-1001",
            "customer_name": "Nguyễn Thị Mai",
            "customer_phone": "0988 123 456",
            "amount_vnd": 650000,
            "source": "kiotviet",
        },
        headers=_headers(auth),
    )
    assert dup_res.status_code == 200
    assert dup_res.json()["lead_id"] == body["lead_id"]


@pytest.mark.asyncio
async def test_pos_order_updates_existing_lead_and_revenue_summary(client: AsyncClient):
    auth = await _onboard(client, email="spa.revenue@example.com")
    workspace_id = auth["active_workspace_id"]

    # 1. Tạo 1 Lead tiềm năng trước đó (ví dụ từ Facebook hỏi giá)
    create_lead_res = await client.post(
        "/leads",
        json={
            "name": "Khách Thảo",
            "phone": "0909 888 777",
            "source": "fanpage",
            "message": "Shop ơi dịch vụ trị nám bao nhiêu ạ?",
        },
        headers=_headers(auth),
    )
    assert create_lead_res.status_code == 201
    lead_id = create_lead_res.json()["id"]

    # 2. Khách đến tiệm làm dịch vụ -> POS bắn đơn hàng về
    pos_res = await client.post(
        "/webhooks/pos",
        params={"workspace_id": workspace_id},
        json={
            "order_id": "POS-2024",
            "customer_name": "Chị Thảo",
            "customer_phone": "0909 888 777",
            "amount_vnd": 2500000,
            "source": "sapo",
            "items": ["Liệu trình trị nám chuyên sâu 5 buổi"],
        },
        headers=_headers(auth),
    )
    assert pos_res.status_code == 200
    assert pos_res.json()["lead_id"] == lead_id
    assert pos_res.json()["stage"] == LeadStage.WON.value

    # 3. Kiểm tra Analytics Summary trả về đúng tổng doanh thu thật
    summary_res = await client.get(
        "/analytics/summary",
        params={"start": "2020-01-01", "end": "2030-01-01"},
        headers=_headers(auth),
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["won_leads"] >= 1
    assert summary["total_revenue_vnd"] >= 2500000
