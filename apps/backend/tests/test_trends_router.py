"""REST API contract tests cho `/workspaces/{workspace_id}/trends` (Milestone #8)."""

import pytest
from httpx import AsyncClient


async def _onboard(client: AsyncClient, email: str) -> tuple[dict[str, str], str]:
    res = await client.post(
        "/auth/sign-up",
        json={"email": email, "password": "secure_password_123", "name": "Chủ Trung Tâm"},
    )
    assert res.status_code == 201, res.text
    tokens = res.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    ws_res = await client.post(
        "/workspaces",
        json={"name": "Trung Tâm Công Nghệ Nhật Minh", "industry": "spa"},
        headers=headers,
    )
    assert ws_res.status_code == 201, ws_res.text
    ws_id = ws_res.json()["id"]

    refreshed = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    auth_headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    return auth_headers, ws_id


@pytest.mark.asyncio
async def test_get_hot_trends_endpoint(client: AsyncClient):
    headers, ws_id = await _onboard(client, "trendscout@havi.vn")

    res = await client.get(f"/workspaces/{ws_id}/trends/hot", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    assert "keyword" in data[0]
    assert "trend_score" in data[0]
    assert "sample_hook" in data[0]


@pytest.mark.asyncio
async def test_synthesize_trend_endpoint(client: AsyncClient):
    headers, ws_id = await _onboard(client, "synthesizetrend@havi.vn")

    res = await client.post(
        f"/workspaces/{ws_id}/trends/synthesize",
        json={
            "trend_id": "trend-career-comparison-2026",
            "target_aspect_ratio": "9:16",
            "duration_seconds": 15,
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["trend_id"] == "trend-career-comparison-2026"
    assert data["caption_style"] == "bold_yellow"
    assert len(data["script_outline"]) == 3


@pytest.mark.asyncio
async def test_refresh_hot_trends_endpoint(client: AsyncClient):
    headers, ws_id = await _onboard(client, "refreshtrends@havi.vn")

    res = await client.post(f"/workspaces/{ws_id}/trends/refresh", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 5
    assert "keyword" in data[0]
    assert data[0]["trend_score"] >= 80
