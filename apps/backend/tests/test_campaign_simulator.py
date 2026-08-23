"""Unit & API tests cho Campaign Simulator & Ads Readiness (Havi Phase 5)."""

from httpx import AsyncClient

from application.services.campaign_simulator import (
    CampaignSimulationInput,
    CampaignSimulator,
)


def test_campaign_simulator_logic():
    simulator = CampaignSimulator()
    req = CampaignSimulationInput(
        objective="messages",
        radius_km=5.0,
        daily_budget_vnd=100000.0,
        duration_days=7,
        target_audience="Phụ huynh có con học cấp 2, 3",
    )

    res = simulator.simulate(req)
    assert res.total_budget_vnd == 700000.0
    assert res.estimated_reach_min > 10000
    assert res.estimated_reach_max > res.estimated_reach_min
    assert res.estimated_conversations_min >= 1
    assert res.estimated_conversations_max > res.estimated_conversations_min
    assert "Havi không cam kết doanh thu" in res.disclaimer
    assert len(res.safety_guardrails) >= 3


async def test_campaign_simulation_api(client: AsyncClient):
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chủ Spa", "email": "spa_sim@havi.vn", "password": "matkhau123"},
    )
    assert signup.status_code == 201
    token = signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_ws = await client.post(
        "/workspaces",
        json={"name": "An Spa", "industry": "spa"},
        headers=headers,
    )
    assert create_ws.status_code == 201

    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": signup.json()["refresh_token"]}
    )
    new_headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}

    sim_res = await client.post(
        "/campaigns/simulate",
        json={
            "objective": "messages",
            "radius_km": 3.0,
            "daily_budget_vnd": 150000.0,
            "duration_days": 10,
            "target_audience": "Nữ 22-45 tuổi quanh Quận 1",
        },
        headers=new_headers,
    )
    assert sim_res.status_code == 200, sim_res.text
    data = sim_res.json()
    assert data["total_budget_vnd"] == 1500000.0
    assert data["estimated_reach_min"] > 0
    assert "Havi không cam kết doanh thu" in data["disclaimer"]
