"""Script thực chiến: Xuất bản Video thật lên tài khoản TikTok đã kết nối."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.db import _engine
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.publish_repository import PublishRepository
from adapters.publishers.tiktok import TikTokPublisher
from application.services.approval_service import ApprovalService
from application.services.publish_service import PublishService
from core.alerts import LoggingAlertSink
from core.enums import Channel, ContentStatus, Platform

WORKSPACE_ID = UUID("0c36abba-e1b1-44c0-96e2-661d1e97f6ab")
USER_ID = UUID("ae9e07a9-cc00-4260-bd8f-443751640bef")
VIDEO_URL = "https://cage-beautiful-headset-membrane.trycloudflare.com/test_tiktok.mp4"


async def publish_live_tiktok():
    print("=" * 60)
    print("🎬 TIẾN HÀNH XUẤT BẢN VIDEO THẬT LÊN TIKTOK TÀI KHOẢN KẾT NỐI")
    print("=" * 60)

    async with AsyncSession(_engine) as session:
        conn_repo = ConnectionRepository(session)
        content_repo = ContentRepository(session)
        publish_repo = PublishRepository(session)
        media_repo = MediaRepository(session)
        event_repo = EventLogRepository(session)

        # 1. Kiểm tra kết nối TikTok
        conn = await conn_repo.get(workspace_id=WORKSPACE_ID, platform=Platform.TIKTOK)
        if not conn:
            print("❌ Chưa tìm thấy kết nối TikTok trong workspace!")
            return

        print(
            f"✅ Đã tìm thấy tài khoản TikTok kết nối: {conn.account_name} (ID: {conn.external_account_id})"
        )

        # 2. Tạo nội dung Video hoàn chỉnh
        title = "3 Bước Chăm Sóc Da Căng Bóng Tại Nhà ✨ Spa An Nhiên"
        video_script = (
            "🌿 Bí quyết thải độc và cấp ẩm cho làn da sau tuần làm việc bận rộn.\n"
            "✨ Chỉ với 3 bước đơn giản mỗi tối cùng Spa An Nhiên!\n\n"
            "#spaannhien #chamsocda #skincare #lamdep #havi"
        )

        job, _ = await content_repo.create_job(
            workspace_id=WORKSPACE_ID,
            raw_inputs=[{"kind": "text", "value": title}],
            idempotency_key=f"live_tiktok_{uuid4().hex}",
        )

        tiktok_item = await content_repo.create_item(
            workspace_id=WORKSPACE_ID,
            job_id=job.id,
            channel=Channel.TIKTOK,
            kind="Video TikTok (9:16)",
            text=video_script,
            media_note=VIDEO_URL,
            status=ContentStatus.PENDING_APPROVAL,
        )
        print(f"✅ Đã tạo Content Item Video (ID: {tiktok_item.id})")

        # 3. Phê duyệt bài
        approval_svc = ApprovalService(content=content_repo, events=event_repo)
        approved_item = await approval_svc.approve(
            workspace_id=WORKSPACE_ID,
            item_id=tiktok_item.id,
            user_id=USER_ID,
            scheduled_at=datetime.now(UTC),
        )
        print(f"✅ Đã DUYỆT BÀI $\\rightarrow$ Chuẩn bị xuất bản ngay: {approved_item.id}")

        # 4. Sử dụng TikTokPublisher thật
        tiktok_publisher = TikTokPublisher()

        publish_svc = PublishService(
            content=content_repo,
            connections=conn_repo,
            publishes=publish_repo,
            events=event_repo,
            media=media_repo,
            alerts=LoggingAlertSink(),
            publishers={Channel.TIKTOK: tiktok_publisher},
        )

        # 5. Đưa vào hàng đợi xuất bản
        publish_job, _ = await publish_repo.enqueue(
            workspace_id=WORKSPACE_ID,
            content_item_id=approved_item.id,
            channel=Channel.TIKTOK,
            scheduled_at=datetime.now(UTC),
        )
        print(f"✅ Đã đưa vào hàng đợi xuất bản (Job ID: {publish_job.id})")

        print("\n🚀 Đang gửi video qua TikTok API (POST /v2/post/publish/video/init/)...")
        res_job = await publish_svc.run_job(publish_job)

        print("\n" + "=" * 60)
        print("📊 KẾT QUẢ XUẤT BẢN:")
        print(f"- Trạng thái: {res_job.status.value}")
        print(f"- TikTok Post ID: {res_job.external_post_id}")
        if res_job.published_at:
            print(f"- Thời gian xuất bản: {res_job.published_at.isoformat()}")
        if res_job.failure_kind:
            print(f"- Loại lỗi: {res_job.failure_kind.value}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(publish_live_tiktok())
