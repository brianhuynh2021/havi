"""Báo cáo chỉ phản ánh công việc vận hành có dữ liệu nguồn trực tiếp."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from domain.policies.scheduling import VIETNAM_TZ


async def _onboard(client: AsyncClient, email: str) -> dict[str, str]:
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Mai", "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    tokens = signup.json()
    created = await client.post(
        "/workspaces",
        json={"name": "Tiệm Mai Q7", "industry": "spa"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert created.status_code == 201, created.text
    refreshed = await client.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    return {"Authorization": f"Bearer {refreshed.json()['access_token']}"}


async def _summary(client: AsyncClient, headers: dict[str, str]) -> dict:
    today = datetime.now(VIETNAM_TZ).date()
    response = await client.get(
        "/analytics/summary",
        params={
            "start": (today - timedelta(days=7)).isoformat(),
            "end": (today + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_empty_workspace_reports_only_zero_operations(client: AsyncClient):
    data = await _summary(client, await _onboard(client, "operations.empty@havi.vn"))

    assert data == {
        "published_posts": 0,
        "inbox_items": 0,
        "replies_sent": 0,
        "failed_posts": 0,
        "change_vs_previous_period": {
            "published_posts": 0.0,
            "inbox_items": 0.0,
            "replies_sent": 0.0,
            "failed_posts": 0.0,
        },
    }


@pytest.mark.asyncio
async def test_inbox_received_and_sent_are_counted(client: AsyncClient):
    headers = await _onboard(client, "operations.inbox@havi.vn")
    inbound = await client.post(
        "/webhooks/dev/simulate",
        json={"content": "Cho mình xin thông tin", "external_message_id": "ops-1"},
        headers=headers,
    )
    assert inbound.status_code == 200, inbound.text
    sent = await client.post(
        f"/inbox/{inbound.json()['id']}/reply",
        json={"text": "Chào bạn, tiệm đã nhận được tin nhắn."},
        headers=headers,
    )
    assert sent.status_code == 200, sent.text

    data = await _summary(client, headers)
    assert data["inbox_items"] == 1
    assert data["replies_sent"] == 1


@pytest.mark.asyncio
async def test_duplicate_webhook_does_not_inflate_inbox_count(client: AsyncClient):
    headers = await _onboard(client, "operations.dedupe@havi.vn")
    payload = {"content": "Xin chào", "external_message_id": "same-message"}
    await client.post("/webhooks/dev/simulate", json=payload, headers=headers)
    await client.post("/webhooks/dev/simulate", json=payload, headers=headers)

    assert (await _summary(client, headers))["inbox_items"] == 1
