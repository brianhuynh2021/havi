"""REST API contract tests cho `/workspaces/{id}/video/render-jobs`."""

import pytest
from httpx import AsyncClient


async def _onboard(client: AsyncClient, email: str) -> tuple[dict[str, str], str]:
    res = await client.post(
        "/auth/sign-up",
        json={"email": email, "password": "secure_password_123", "name": "Chủ Spa"},
    )
    tokens = res.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    ws_res = await client.post(
        "/workspaces",
        json={"name": "Havi Spa Studio", "industry": "spa"},
        headers=headers,
    )
    ws_id = ws_res.json()["id"]

    refreshed = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    auth_headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    return auth_headers, ws_id


@pytest.mark.asyncio
async def test_video_render_router_full_api_lifecycle(client: AsyncClient):
    headers, ws_id = await _onboard(client, "videostudio@havi.vn")

    # 1. Create Render Job
    create_res = await client.post(
        f"/workspaces/{ws_id}/video/render-jobs",
        json={
            "title": "Shorts Giảm Mụn Chuyên Sâu",
            "target_aspect_ratio": "9:16",
            "edit_plan": {
                "target_aspect_ratio": "9:16",
                "target_duration_seconds": 20.0,
                "cuts": [{"start_ms": 0, "end_ms": 20000, "zoom_scale": 1.0}],
                "captions": [
                    {
                        "text": "3 BƯỚC HẾT MỤN",
                        "start_ms": 0,
                        "end_ms": 3000,
                        "style": "bold_yellow",
                    }
                ],
                "audio": {"normalize_db": -14.0, "bg_music_volume": 0.2},
            },
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    job_data = create_res.json()
    job_id = job_data["id"]
    assert job_data["title"] == "Shorts Giảm Mụn Chuyên Sâu"
    assert job_data["status"] == "queued"
    assert job_data["progress_percent"] == 0

    # 2. Get Job Details & Progress
    get_res = await client.get(
        f"/workspaces/{ws_id}/video/render-jobs/{job_id}",
        headers=headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == job_id

    # 3. List Jobs
    list_res = await client.get(
        f"/workspaces/{ws_id}/video/render-jobs",
        headers=headers,
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1
    assert any(j["id"] == job_id for j in list_res.json()["items"])

    # 4. Cancel Job
    cancel_res = await client.post(
        f"/workspaces/{ws_id}/video/render-jobs/{job_id}/cancel",
        headers=headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["ok"] is True

    # 5. Retry Job
    retry_res = await client.post(
        f"/workspaces/{ws_id}/video/render-jobs/{job_id}/retry",
        headers=headers,
    )
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_video_render_router_validation_error(client: AsyncClient):
    headers, ws_id = await _onboard(client, "videovalidate@havi.vn")

    bad_res = await client.post(
        f"/workspaces/{ws_id}/video/render-jobs",
        json={
            "title": "Bad Plan",
            "target_aspect_ratio": "9:16",
            "edit_plan": {
                "target_aspect_ratio": "4:3",  # invalid
                "target_duration_seconds": 10.0,
            },
        },
        headers=headers,
    )
    assert bad_res.status_code == 422
