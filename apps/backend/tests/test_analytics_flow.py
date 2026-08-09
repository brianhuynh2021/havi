"""Analytics tối thiểu cho Tuần 8: dashboard dùng dữ liệu thật, không fixture."""

from datetime import UTC, datetime
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.event_log_repository import EventLogRepository
from core.enums import Channel, ContentStatus
from core.events import EventLogEntry
from domain.models.content import ContentItem


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chị Hương", "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()
    create = await client.post(
        "/workspaces",
        json={"name": "Spa An Nhiên", "industry": "spa"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert create.status_code == 201, create.text
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def _add_item(
    session: AsyncSession,
    *,
    workspace_id: str,
    status: ContentStatus,
    channel: Channel = Channel.FACEBOOK_PAGE,
) -> ContentItem:
    item = ContentItem(
        workspace_id=UUID(workspace_id),
        channel=channel,
        kind="Bài ảnh",
        text="Ưu đãi gội đầu thảo dược cuối tuần này.",
        status=status,
        published_at=(
            datetime(2026, 8, 9, 6, 30, tzinfo=UTC)
            if status == ContentStatus.PUBLISHED
            else None
        ),
    )
    session.add(item)
    await session.flush()
    return item


async def test_dashboard_workspace_moi_tra_so_0(client: AsyncClient):
    token_pair = await _onboard(client, email="analytics-empty@havi.vn")

    response = await client.get("/analytics/dashboard", headers=_headers(token_pair))

    assert response.status_code == 200, response.text
    assert response.json() == {
        "drafts": 0,
        "pending_approval": 0,
        "scheduled": 0,
        "published": 0,
        "failed": 0,
    }


async def test_dashboard_dem_content_item_theo_workspace(
    client: AsyncClient, db_session: AsyncSession
):
    token_a = await _onboard(client, email="analytics-a@havi.vn")
    token_b = await _onboard(client, email="analytics-b@havi.vn")
    await _add_item(
        db_session,
        workspace_id=token_a["active_workspace_id"],
        status=ContentStatus.PENDING_APPROVAL,
    )
    await _add_item(
        db_session,
        workspace_id=token_a["active_workspace_id"],
        status=ContentStatus.SCHEDULED,
    )
    await _add_item(
        db_session,
        workspace_id=token_a["active_workspace_id"],
        status=ContentStatus.PUBLISHED,
    )
    await _add_item(
        db_session,
        workspace_id=token_a["active_workspace_id"],
        status=ContentStatus.DEAD_LETTER,
    )
    await _add_item(
        db_session,
        workspace_id=token_b["active_workspace_id"],
        status=ContentStatus.PUBLISHED,
    )

    response = await client.get("/analytics/dashboard", headers=_headers(token_a))

    assert response.status_code == 200, response.text
    assert response.json() == {
        "drafts": 0,
        "pending_approval": 1,
        "scheduled": 1,
        "published": 1,
        "failed": 1,
    }


async def test_analytics_summary_va_attribution_khong_lan_workspace_khac(
    client: AsyncClient, db_session: AsyncSession
):
    token_a = await _onboard(client, email="analytics-summary-a@havi.vn")
    token_b = await _onboard(client, email="analytics-summary-b@havi.vn")
    await _add_item(
        db_session,
        workspace_id=token_a["active_workspace_id"],
        status=ContentStatus.PUBLISHED,
        channel=Channel.FACEBOOK_PAGE,
    )
    await _add_item(
        db_session,
        workspace_id=token_a["active_workspace_id"],
        status=ContentStatus.PUBLISHED,
        channel=Channel.ZALO_OA,
    )
    await _add_item(
        db_session,
        workspace_id=token_b["active_workspace_id"],
        status=ContentStatus.PUBLISHED,
        channel=Channel.GOOGLE_BUSINESS,
    )
    params = {"start": "2026-08-01", "end": "2026-08-31"}

    summary = await client.get(
        "/analytics/summary", params=params, headers=_headers(token_a)
    )
    attribution = await client.get(
        "/analytics/attribution", params=params, headers=_headers(token_a)
    )

    assert summary.status_code == 200, summary.text
    assert summary.json()["published_posts"] == 2
    assert attribution.status_code == 200, attribution.text
    assert {item["channel"]: item["customers"] for item in attribution.json()} == {
        "facebook_page": 1,
        "zalo_oa": 1,
    }


async def test_timeseries_monthly_tra_4_ky_khac_nhau(client: AsyncClient):
    token_pair = await _onboard(client, email="analytics-series@havi.vn")

    response = await client.get(
        "/analytics/timeseries",
        params={"metric": "published_posts", "granularity": "month"},
        headers=_headers(token_pair),
    )

    assert response.status_code == 200, response.text
    points = response.json()["points"]
    assert len(points) == 4
    assert len({point["period"] for point in points}) == 4


async def test_event_log_query_scope_theo_workspace_va_filter_duoc(
    client: AsyncClient, db_session: AsyncSession
):
    token_a = await _onboard(client, email="analytics-events-a@havi.vn")
    token_b = await _onboard(client, email="analytics-events-b@havi.vn")
    job_id = UUID("00000000-0000-0000-0000-000000000123")
    events = EventLogRepository(db_session)
    await events.record(
        EventLogEntry(
            workspace_id=UUID(token_a["active_workspace_id"]),
            job_id=job_id,
            request_id="req_a_success",
            job_kind="content.generate",
            input_summary="1 raw input",
            output_summary="drafts=3",
            tokens_in=100,
            tokens_out=200,
            provider="gemini",
            duration_ms=1234,
        )
    )
    await events.record(
        EventLogEntry(
            workspace_id=UUID(token_a["active_workspace_id"]),
            job_id=job_id,
            request_id="req_a_error",
            job_kind="content.generate",
            input_summary="1 raw input",
            output_summary="schema failed",
            tokens_in=50,
            tokens_out=10,
            provider="anthropic",
            duration_ms=100,
            error="schema_error",
        )
    )
    await events.record(
        EventLogEntry(
            workspace_id=UUID(token_b["active_workspace_id"]),
            job_id=job_id,
            request_id="req_b_hidden",
            job_kind="content.generate",
            input_summary="workspace B",
            output_summary="không được thấy",
            provider="gemini",
        )
    )

    response = await client.get(
        "/analytics/events",
        params={"job_id": str(job_id), "error_only": "true"},
        headers=_headers(token_a),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["workspace_id"] == token_a["active_workspace_id"]
    assert body["items"][0]["request_id"] == "req_a_error"
    assert body["items"][0]["provider"] == "anthropic"
    assert body["items"][0]["error"] == "schema_error"
    assert "không được thấy" not in response.text

    by_request = await client.get(
        "/analytics/events",
        params={"request_id": "req_a_success"},
        headers=_headers(token_a),
    )
    assert by_request.status_code == 200, by_request.text
    assert by_request.json()["total"] == 1
    assert by_request.json()["items"][0]["provider"] == "gemini"
