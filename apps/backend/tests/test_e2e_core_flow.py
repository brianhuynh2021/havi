"""Local E2E: signup → draft → approve → fake publish → report.

This is intentionally in-process instead of browser-driven. It keeps the core
value loop isolated, fast, and free of real LLM/Facebook side effects while still
using the HTTP API for user-facing boundaries and real service/repository code
for worker-side steps.
"""

import json
import os
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.llm.fake import FakeProvider
from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.publish_repository import PublishRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from adapters.publishers.fake import FakePublisher
from application.services.content_engine import ContentEngine
from application.services.publish_service import PublishService
from core.config import get_settings
from core.enums import Channel, Platform
from domain.policies.provider_router import ProviderRouter

GOOD_OUTPUT = json.dumps(
    {
        "drafts": [
            {
                "channel": "facebook_page",
                "kind": "Bài ảnh",
                "text": "Gội đầu thảo dược cuối tuần này có ưu đãi nhỏ cho khách quen nha.",
                "media_note": "Chụp 1 tấm lúc đang gội",
            },
            {
                "channel": "zalo_oa",
                "kind": "Tin Zalo",
                "text": "Chị ơi, tuần này tiệm có ưu đãi gội đầu thảo dược, chị ghé nha.",
            },
            {
                "channel": "google_business",
                "kind": "Cập nhật Google",
                "text": "Spa cập nhật dịch vụ gội đầu thảo dược cuối tuần này.",
            },
        ]
    },
    ensure_ascii=False,
)


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def test_signup_to_draft_approve_fake_publish_and_report(
    client: AsyncClient, db_session: AsyncSession
):
    """Core beta smoke test, isolated by email/workspace and rolled back by fixture."""
    os.environ["HAVI_TOKEN_ENCRYPTION_KEY"] = "3Vn8Qm2xLp7YtZa1Rk4Wc6Bd9Ef0Gh5Jj2Kl3Mn4Op8="
    get_settings.cache_clear()

    email = f"e2e-{uuid4().hex[:12]}@havi.vn"
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chị Hương", "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()

    create_workspace = await client.post(
        "/workspaces",
        json={"name": f"Spa E2E {uuid4().hex[:6]}", "industry": "spa"},
        headers=_headers(token_pair),
    )
    assert create_workspace.status_code == 201, create_workspace.text

    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    assert refreshed.status_code == 200, refreshed.text
    token_pair = refreshed.json()
    workspace_id = UUID(token_pair["active_workspace_id"])

    job_response = await client.post(
        "/content/jobs",
        json={"raw_inputs": [{"kind": "text", "text": "Tuần này ưu đãi gội đầu"}]},
        headers=_headers(token_pair) | {"Idempotency-Key": f"e2e-{uuid4()}"},
    )
    assert job_response.status_code == 202, job_response.text
    job = job_response.json()

    llm = FakeProvider(response_text=GOOD_OUTPUT)
    engine = ContentEngine(
        content=ContentRepository(db_session),
        workspaces=WorkspaceRepository(db_session),
        profiles=BrandProfileRepository(db_session),
        media=MediaRepository(db_session),
        events=EventLogRepository(db_session),
        router=ProviderRouter({llm.provider: llm}),
    )
    generated = await engine.generate_drafts(workspace_id=workspace_id, job_id=UUID(job["id"]))
    assert len(generated.items) == 3

    content = await client.get(
        "/content",
        params={"status": "pending_approval"},
        headers=_headers(token_pair),
    )
    assert content.status_code == 200, content.text
    fb_item = next(item for item in content.json()["items"] if item["channel"] == "facebook_page")
    zalo_item = next(item for item in content.json()["items"] if item["channel"] == "zalo_oa")

    scheduled_at = datetime.now(UTC) - timedelta(minutes=1)
    for item in (fb_item, zalo_item):
        approve = await client.post(
            f"/content/{item['id']}/approve",
            json={"scheduled_at": scheduled_at.isoformat()},
            headers=_headers(token_pair),
        )
        assert approve.status_code == 200, approve.text
        assert approve.json()["status"] == "scheduled"

    await ConnectionRepository(db_session).upsert(
        workspace_id=workspace_id,
        platform=Platform.FACEBOOK,
        access_token="fake-page-token",
        external_account_id="page-e2e",
        account_name="E2E Facebook Page",
    )
    await ConnectionRepository(db_session).upsert(
        workspace_id=workspace_id,
        platform=Platform.ZALO_OA,
        access_token="fake-zalo-token",
        external_account_id="zalo-e2e",
        account_name="E2E Zalo OA",
    )

    fb_publisher = FakePublisher(channel=Channel.FACEBOOK_PAGE, post_id="e2e_fb_post")
    zalo_publisher = FakePublisher(channel=Channel.ZALO_OA, post_id="e2e_zalo_post")
    publish_service = PublishService(
        content=ContentRepository(db_session),
        connections=ConnectionRepository(db_session),
        publishes=PublishRepository(db_session),
        events=EventLogRepository(db_session),
        publishers={
            Channel.FACEBOOK_PAGE: fb_publisher,
            Channel.ZALO_OA: zalo_publisher,
        },
    )
    dispatch = await publish_service.dispatch_due(now=datetime.now(UTC))
    assert dispatch.enqueued == 2
    jobs = await publish_service.run_due(now=datetime.now(UTC))
    assert len(jobs) == 2
    assert len(fb_publisher.calls) == 1
    assert len(zalo_publisher.calls) == 1

    for item in (fb_item, zalo_item):
        published = await client.get(f"/content/{item['id']}", headers=_headers(token_pair))
        assert published.status_code == 200, published.text
        assert published.json()["status"] == "published"

    today = date.today().isoformat()
    summary = await client.get(
        "/analytics/summary",
        params={"start": today, "end": today},
        headers=_headers(token_pair),
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["published_posts"] == 2

    operations = await client.get(
        "/analytics/operations",
        params={"start": today, "end": today},
        headers=_headers(token_pair),
    )
    assert operations.status_code == 200, operations.text
    assert operations.json()["publish"]["succeeded"] == 2
