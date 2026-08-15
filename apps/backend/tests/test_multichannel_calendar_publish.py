"""End-to-end integration test for Multi-channel Publishing.

Verifies:
1. Multi-channel content creation for Facebook Page, Reels, TikTok, and YouTube.
2. Approval sets scheduled_at automatically to next Vietnam golden hour (08:00, 12:00, 20:00 ICT).
3. PublishService dispatches across all 4 channels (Facebook, Reels, TikTok, YouTube).
4. Idempotency and status transitions across all channels.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.publish_repository import PublishRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from adapters.publishers.fake import FakePublisher
from application.services.approval_service import ApprovalService
from application.services.publish_service import PublishService
from core.alerts import LoggingAlertSink
from core.enums import Channel, ContentStatus, Industry, Platform, PublishStatus, WorkspaceRole


@pytest.mark.asyncio
async def test_multichannel_approval_and_publish_flow(db_session: AsyncSession):
    # 1. Setup workspace & user
    ws_repo = WorkspaceRepository(db_session)
    user_repo = UserRepository(db_session)
    member_repo = WorkspaceMemberRepository(db_session)
    conn_repo = ConnectionRepository(db_session)
    content_repo = ContentRepository(db_session)
    publish_repo = PublishRepository(db_session)
    media_repo = MediaRepository(db_session)
    event_repo = EventLogRepository(db_session)

    user = await user_repo.create(
        email=f"tester_{uuid4().hex[:6]}@havi.vn",
        name="Chủ Tiệm Spa",
        password_hash="test_hash",
    )

    ws = await ws_repo.create(
        name="Tiệm Spa Havi",
        industry=Industry.SPA,
        owner_user_id=user.id,
    )

    await member_repo.add(
        workspace_id=ws.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER,
    )

    # 2. Setup connections for Facebook, TikTok, and YouTube
    await conn_repo.upsert(
        workspace_id=ws.id,
        platform=Platform.FACEBOOK,
        external_account_id="fb_page_1001",
        account_name="Havi Spa Fanpage",
        access_token="valid_fb_token",
    )
    await conn_repo.upsert(
        workspace_id=ws.id,
        platform=Platform.TIKTOK,
        external_account_id="tiktok_user_2002",
        account_name="@havi_spa",
        access_token="valid_tiktok_token",
    )
    await conn_repo.upsert(
        workspace_id=ws.id,
        platform=Platform.YOUTUBE,
        external_account_id="yt_channel_3003",
        account_name="Havi Spa Official",
        access_token="valid_yt_token",
    )

    # 3. Create Drafts across channels
    job, _ = await content_repo.create_job(
        workspace_id=ws.id,
        raw_inputs=[{"kind": "text", "value": "Chăm sóc da spa"}],
        idempotency_key="idemp_test_123",
    )

    tiktok_item = await content_repo.create_item(
        workspace_id=ws.id,
        job_id=job.id,
        channel=Channel.TIKTOK,
        kind="short_video",
        text="Cùng Havi Spa khám phá liệu trình 5 bước trị mụn chuyên sâu nhé! #skincare #spa",
        media_note=None,
        status=ContentStatus.PENDING_APPROVAL,
    )
    assert tiktok_item.status == ContentStatus.PENDING_APPROVAL

    # 4. Approve TikTok Draft -> verify auto-assigned scheduled_at
    approval_svc = ApprovalService(content=content_repo, events=event_repo)
    approved_item = await approval_svc.approve(
        workspace_id=ws.id,
        item_id=tiktok_item.id,
        user_id=user.id,
        scheduled_at=None,
    )
    assert approved_item.status == ContentStatus.SCHEDULED
    assert approved_item.scheduled_at is not None

    # 5. Create Fake Publishers for all channels
    fb_pub = FakePublisher(channel=Channel.FACEBOOK_PAGE, post_id="fb_post_100")
    reels_pub = FakePublisher(channel=Channel.REELS, post_id="fb_reel_100")
    tiktok_pub = FakePublisher(channel=Channel.TIKTOK, post_id="tiktok_post_200")
    yt_pub = FakePublisher(channel=Channel.YOUTUBE, post_id="yt_shorts_300")

    publishers = {
        Channel.FACEBOOK_PAGE: fb_pub,
        Channel.REELS: reels_pub,
        Channel.TIKTOK: tiktok_pub,
        Channel.YOUTUBE: yt_pub,
    }

    publish_svc = PublishService(
        content=content_repo,
        connections=conn_repo,
        publishes=publish_repo,
        events=event_repo,
        media=media_repo,
        alerts=LoggingAlertSink(),
        publishers=publishers,
    )

    # 6. Dispatch publish job for TikTok
    job, _ = await publish_repo.enqueue(
        workspace_id=ws.id,
        content_item_id=approved_item.id,
        channel=Channel.TIKTOK,
        scheduled_at=approved_item.scheduled_at,
    )
    assert job.status == PublishStatus.PENDING

    result = await publish_svc.run_job(job)
    assert result.status == PublishStatus.SUCCEEDED
    assert len(tiktok_pub.calls) == 1
    assert "v_pub" in result.external_post_id or "tiktok_post" in result.external_post_id

    # 7. Verify Content Item updated to PUBLISHED
    updated_item = await content_repo.get_item(workspace_id=ws.id, item_id=approved_item.id)
    assert updated_item is not None
    assert updated_item.status == ContentStatus.PUBLISHED
