"""Integration test suite cho CRM Nudges Router."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import LeadSource, LeadStage
from domain.models.lead import Lead


async def _onboard(client: AsyncClient, email: str) -> tuple[dict[str, str], str]:
    res = await client.post(
        "/auth/sign-up",
        json={"email": email, "password": "secure_password_123", "name": "Chủ Spa"},
    )
    tokens = res.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    ws_res = await client.post(
        "/workspaces",
        json={"name": "Tiệm Nail Xinh", "industry": "spa"},
        headers=headers,
    )
    ws_id = ws_res.json()["id"]

    refreshed = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    auth_headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    return auth_headers, ws_id


@pytest.mark.asyncio
async def test_crm_nudge_router_flow(client: AsyncClient, db_session: AsyncSession):
    headers, ws_id_str = await _onboard(client, f"nudge_{uuid.uuid4()}@havi.vn")
    ws_id = uuid.UUID(ws_id_str)

    # Thêm lead 40 ngày trước
    lead = Lead(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        name="Chị Hương",
        phone="0912345678",
        source=LeadSource.FANPAGE,
        stage=LeadStage.WON,
    )
    db_session.add(lead)
    await db_session.flush()
    await db_session.execute(
        update(Lead)
        .where(Lead.id == lead.id)
        .values(created_at=datetime.now(UTC) - timedelta(days=40))
    )
    await db_session.commit()

    # 1. Trigger scan
    scan_res = await client.post(
        f"/workspaces/{ws_id}/crm/nudges/scan?inactive_days=30",
        headers=headers,
    )
    assert scan_res.status_code == 200, scan_res.text
    nudges = scan_res.json()
    assert len(nudges) == 1
    nudge_id = nudges[0]["id"]
    assert nudges[0]["status"] == "pending_approval"
    assert "Chị Hương" in nudges[0]["message"]

    # 2. List nudges
    list_res = await client.get(
        f"/workspaces/{ws_id}/crm/nudges",
        headers=headers,
    )
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == nudge_id

    # 3. Approve nudge
    approve_res = await client.post(
        f"/workspaces/{ws_id}/crm/nudges/{nudge_id}/approve",
        headers=headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "sent"

    # 4. Dismiss endpoint test
    dismiss_res = await client.post(
        f"/workspaces/{ws_id}/crm/nudges/{nudge_id}/dismiss",
        headers=headers,
    )
    assert dismiss_res.status_code == 200
    assert dismiss_res.json()["status"] == "dismissed"
