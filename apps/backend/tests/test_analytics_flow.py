"""Analytics tối thiểu cho Tuần 8: dashboard dùng dữ liệu thật, không fixture."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.event_log_repository import EventLogRepository
from core.enums import Channel, ContentStatus, PublishStatus
from core.events import EventLogEntry
from domain.models.content import ContentItem
from domain.models.publish import PublishJob
from domain.policies import pricing


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
            datetime(2026, 8, 9, 6, 30, tzinfo=UTC) if status == ContentStatus.PUBLISHED else None
        ),
    )
    session.add(item)
    await session.flush()
    return item


async def _add_event(
    session: AsyncSession,
    *,
    workspace_id: str,
    created_at: datetime,
    provider: str,
    duration_ms: int,
    tokens_in: int = 0,
    tokens_out: int = 0,
    error: str | None = None,
) -> None:
    row = await EventLogRepository(session).record(
        EventLogEntry(
            workspace_id=UUID(workspace_id),
            job_id=UUID("00000000-0000-0000-0000-000000000456"),
            request_id="req_ops",
            job_kind="content.generate",
            input_summary="raw input",
            output_summary="drafts",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            provider=provider,
            duration_ms=duration_ms,
            error=error,
        )
    )
    row.created_at = created_at
    await session.flush()


async def _add_publish_job(
    session: AsyncSession,
    *,
    workspace_id: str,
    status: PublishStatus,
    updated_at: datetime,
) -> None:
    item = await _add_item(session, workspace_id=workspace_id, status=ContentStatus.SCHEDULED)
    job = PublishJob(
        workspace_id=UUID(workspace_id),
        content_item_id=item.id,
        channel=Channel.FACEBOOK_PAGE,
        idempotency_key=f"{item.id}:{status.value}:{updated_at.isoformat()}",
        status=status,
        scheduled_at=updated_at - timedelta(minutes=5),
        updated_at=updated_at,
    )
    session.add(job)
    await session.flush()


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
        "total_connections": 0,
        "broken_connections": 0,
        "unhandled_inbox": 0,
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
        "total_connections": 0,
        "broken_connections": 0,
        "unhandled_inbox": 0,
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

    summary = await client.get("/analytics/summary", params=params, headers=_headers(token_a))
    attribution = await client.get(
        "/analytics/attribution", params=params, headers=_headers(token_a)
    )

    assert summary.status_code == 200, summary.text
    assert summary.json()["published_posts"] == 2
    assert attribution.status_code == 200, attribution.text
    assert {item["channel"]: item["posts"] for item in attribution.json()} == {
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


async def test_chi_phi_moi_ban_nhap_chia_cho_so_nhap_DUOC_DUYET(
    client: AsyncClient, db_session: AsyncSession
):
    """Mẫu số là nháp được duyệt, không phải số sự kiện sinh nội dung.

    Bản trước lấy `approved_draft_count = số event có job_kind chứa "content"`.
    Một job sinh nhiều nháp và người dùng chỉ dùng vài cái, nên con số đó thấp
    hơn chi phí thật đúng bằng tỷ lệ nháp bị vứt — sai theo hướng lạc quan, tức
    là loại sai khiến người ta giữ nguyên một bảng giá đang lỗ.

    Ở đây: 1 lượt gọi LLM sinh 4 nháp, người dùng duyệt 1. Chi phí cho bài lên
    được kênh phải là **toàn bộ** tiền của lượt gọi đó, không phải một phần tư.
    """
    token_pair = await _onboard(client, email="analytics-unit-econ@havi.vn")
    workspace_id = token_pair["active_workspace_id"]
    inside = datetime(2026, 8, 9, 7, 0, tzinfo=UTC)

    await _add_event(
        db_session,
        workspace_id=workspace_id,
        created_at=inside,
        provider="gemini",
        duration_ms=1200,
        tokens_in=4_000,
        tokens_out=6_000,
    )

    # 4 nháp sinh ra trong kỳ, đúng 1 được duyệt.
    items = [
        await _add_item(
            db_session, workspace_id=workspace_id, status=ContentStatus.PENDING_APPROVAL
        )
        for _ in range(4)
    ]
    for item in items:
        item.created_at = inside
    items[0].status = ContentStatus.APPROVED
    items[0].approved_at = inside + timedelta(minutes=5)
    await db_session.flush()

    response = await client.get(
        "/analytics/operations",
        params={"start": "2026-08-09", "end": "2026-08-09"},
        headers=_headers(token_pair),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["generated_draft_count"] == 4
    assert body["approved_draft_count"] == 1
    assert body["draft_usage_rate"] == 0.25

    content_cost = pricing.cost_vnd(
        tokens_in=4_000, tokens_out=6_000, model=None, provider="gemini"
    )
    assert body["est_cost_per_approved_draft_vnd"] == round(round(content_cost) / 1)

    # Chốt hướng sai: nếu ai đó đổi mẫu số về số nháp SINH RA, con số sẽ nhỏ đi
    # bốn lần và assert này vỡ.
    assert body["est_cost_per_approved_draft_vnd"] > round(content_cost / 4)


async def test_khong_co_nhap_nao_duoc_duyet_thi_khong_bia_chi_phi(
    client: AsyncClient, db_session: AsyncSession
):
    """Sinh nháp nhưng chưa ai duyệt → chia cho 0. Trả 0, không trả số bịa."""
    token_pair = await _onboard(client, email="analytics-unit-econ-zero@havi.vn")
    workspace_id = token_pair["active_workspace_id"]
    inside = datetime(2026, 8, 9, 7, 0, tzinfo=UTC)

    await _add_event(
        db_session,
        workspace_id=workspace_id,
        created_at=inside,
        provider="gemini",
        duration_ms=800,
        tokens_in=2_000,
        tokens_out=3_000,
    )
    item = await _add_item(
        db_session, workspace_id=workspace_id, status=ContentStatus.PENDING_APPROVAL
    )
    item.created_at = inside
    await db_session.flush()

    response = await client.get(
        "/analytics/operations",
        params={"start": "2026-08-09", "end": "2026-08-09"},
        headers=_headers(token_pair),
    )

    body = response.json()
    assert body["generated_draft_count"] == 1
    assert body["approved_draft_count"] == 0
    assert body["draft_usage_rate"] == 0
    assert body["est_cost_per_approved_draft_vnd"] == 0


async def test_operations_metrics_dem_log_va_publish_job_theo_workspace(
    client: AsyncClient, db_session: AsyncSession
):
    token_a = await _onboard(client, email="analytics-ops-a@havi.vn")
    token_b = await _onboard(client, email="analytics-ops-b@havi.vn")
    inside = datetime(2026, 8, 9, 7, 0, tzinfo=UTC)
    outside = datetime(2026, 8, 10, 18, 0, tzinfo=UTC)

    await _add_event(
        db_session,
        workspace_id=token_a["active_workspace_id"],
        created_at=inside,
        provider="gemini",
        duration_ms=100,
        tokens_in=10,
        tokens_out=20,
    )
    await _add_event(
        db_session,
        workspace_id=token_a["active_workspace_id"],
        created_at=inside + timedelta(minutes=1),
        provider="gemini",
        duration_ms=900,
        tokens_in=30,
        tokens_out=40,
        error="provider_timeout",
    )
    await _add_event(
        db_session,
        workspace_id=token_b["active_workspace_id"],
        created_at=inside,
        provider="anthropic",
        duration_ms=5000,
        tokens_in=999,
        tokens_out=999,
        error="hidden",
    )
    await _add_event(
        db_session,
        workspace_id=token_a["active_workspace_id"],
        created_at=outside,
        provider="gemini",
        duration_ms=5000,
        tokens_in=500,
        tokens_out=500,
    )
    await _add_publish_job(
        db_session,
        workspace_id=token_a["active_workspace_id"],
        status=PublishStatus.SUCCEEDED,
        updated_at=inside,
    )
    await _add_publish_job(
        db_session,
        workspace_id=token_a["active_workspace_id"],
        status=PublishStatus.DEAD_LETTER,
        updated_at=inside + timedelta(minutes=1),
    )
    await _add_publish_job(
        db_session,
        workspace_id=token_b["active_workspace_id"],
        status=PublishStatus.DEAD_LETTER,
        updated_at=inside,
    )

    response = await client.get(
        "/analytics/operations",
        params={"start": "2026-08-09", "end": "2026-08-09"},
        headers=_headers(token_a),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["event_count"] == 2
    assert body["error_count"] == 1
    assert body["error_rate"] == 0.5
    assert body["avg_duration_ms"] == 500
    assert body["p95_duration_ms"] == 900
    assert body["tokens_in"] == 40
    assert body["tokens_out"] == 60
    assert body["tokens_total"] == 100
    # Chi phí lấy từ `domain/policies/pricing.py`, không hardcode con số ở đây:
    # bảng giá sẽ được cập nhật định kỳ, và một test vỡ mỗi lần đổi giá thì
    # người ta sửa test cho qua chứ không đọc nó. Điều cần khoá là *wiring* —
    # tiền được tính theo provider/model của từng dòng — chứ không phải giá
    # hôm nay là bao nhiêu.
    expected_cost = round(
        pricing.cost_vnd(tokens_in=10, tokens_out=20, model=None, provider="gemini")
        + pricing.cost_vnd(tokens_in=30, tokens_out=40, model=None, provider="gemini")
    )
    assert body["providers"] == [
        {
            "provider": "gemini",
            "event_count": 2,
            "error_count": 1,
            "tokens_total": 100,
            "cost_vnd": expected_cost,
        }
    ]
    # Dòng không có `model` phải rơi về giá provider, và giá đó là mức ĐẮT NHẤT
    # của nhóm — sai số nghiêng về phía thận trọng.
    assert expected_cost > 0
    assert body["pricing_as_of"] == pricing.AS_OF.isoformat()
    assert body["publish"] == {
        "total": 2,
        "succeeded": 1,
        "dead_letter": 1,
        "success_rate": 0.5,
        "dead_letter_rate": 0.5,
    }


async def test_operations_tach_rien_job_tao_bai_cham_qua_20_giay(
    client: AsyncClient, db_session: AsyncSession
):
    """P95 chung không được che một content job vượt SLA P1."""
    token = await _onboard(client, email="analytics-slow-content@havi.vn")
    inside = datetime(2026, 8, 9, 7, 0, tzinfo=UTC)
    for index, duration_ms in enumerate((19_999, 20_001)):
        await _add_event(
            db_session,
            workspace_id=token["active_workspace_id"],
            created_at=inside + timedelta(minutes=index),
            provider="gemini",
            duration_ms=duration_ms,
        )

    response = await client.get(
        "/analytics/operations",
        params={"start": "2026-08-09", "end": "2026-08-09"},
        headers=_headers(token),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["content_generation_count"] == 2
    assert body["slow_content_generation_count"] == 1
    assert body["content_generation_p95_ms"] == 20_001
    assert body["slow_content_generation_threshold_ms"] == 20_000


async def test_events_loc_theo_content_item_id(
    client: AsyncClient, db_session: AsyncSession
):
    token = await _onboard(client, email="analytics-content-item-filter@havi.vn")
    workspace_id = UUID(token["active_workspace_id"])
    target_item_id = UUID("11111111-1111-1111-1111-111111111111")
    other_item_id = UUID("22222222-2222-2222-2222-222222222222")

    repo = EventLogRepository(db_session)
    await repo.record(
        EventLogEntry(
            workspace_id=workspace_id,
            content_item_id=target_item_id,
            job_kind="publish.run_job",
            input_summary="target post publish",
            output_summary="published",
        )
    )
    await repo.record(
        EventLogEntry(
            workspace_id=workspace_id,
            content_item_id=other_item_id,
            job_kind="publish.run_job",
            input_summary="other post publish",
            output_summary="published",
        )
    )

    response = await client.get(
        "/analytics/events",
        params={"content_item_id": str(target_item_id)},
        headers=_headers(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["content_item_id"] == str(target_item_id)
    assert body["items"][0]["input_summary"] == "target post publish"
