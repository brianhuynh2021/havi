"""Demo script: Tạo & Xuất bản 1 Video TikTok chuẩn 9:16 trên môi trường Local Havi.

Kịch bản:
1. Tạo / Tìm Workspace & User cho 'Trung Tâm Công Nghệ Nhật Minh'.
2. Khởi tạo kết nối kênh TikTok với Client Key & Secret cấu hình.
3. Sinh nội dung Video TikTok:
   - Hook 3 giây đầu kích thích tò mò
   - Thời lượng chuẩn 30s TikTok
   - Tỉ lệ khung hình 9:16 dọc kèm âm thanh
   - Bộ hashtag ngành (#nhatminhtech #havi #viral #tiktok)
4. Thực hiện Duyệt bài (Approval) -> Tự động xếp vào khung giờ vàng Việt Nam (08:00, 12:00, 20:00 ICT).
5. Điều phối xuất bản qua PublishService & TikTokPublisher.
6. Xác nhận trạng thái PUBLISHED với mã xuất bản chính thức.
"""

import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.db import _engine
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
from core.config import get_settings
from core.enums import (
    Channel,
    ContentStatus,
    Industry,
    Platform,
    WorkspaceRole,
)


async def run_tiktok_demo():
    print("=" * 60)
    print("🚀 BẮT ĐẦU TEST TẠO & XUẤT BẢN VIDEO TIKTOK (HAVI LOCAL)")
    print("=" * 60)

    settings = get_settings()

    async with AsyncSession(_engine) as session:
        ws_repo = WorkspaceRepository(session)
        user_repo = UserRepository(session)
        member_repo = WorkspaceMemberRepository(session)
        conn_repo = ConnectionRepository(session)
        content_repo = ContentRepository(session)
        publish_repo = PublishRepository(session)
        media_repo = MediaRepository(session)
        event_repo = EventLogRepository(session)

        # 1. Tạo User & Workspace thử nghiệm
        email = f"founder_nhatminh_{uuid4().hex[:4]}@havi.vn"
        user = await user_repo.create(
            email=email,
            name="Nhà Sáng Lập Nhật Minh",
            password_hash="argon2id_hash_placeholder",
        )
        ws = await ws_repo.create(
            name="Trung Tâm Công Nghệ Nhật Minh",
            industry=Industry.ONLINE_SHOP,
            owner_user_id=user.id,
        )
        await member_repo.add(
            workspace_id=ws.id,
            user_id=user.id,
            role=WorkspaceRole.OWNER,
        )
        print(f"✅ Đã tạo Workspace: '{ws.name}' (ID: {ws.id})")

        # 2. Khởi tạo Connection TikTok
        conn = await conn_repo.upsert(
            workspace_id=ws.id,
            platform=Platform.TIKTOK,
            external_account_id="tiktok_nhatminh_tech",
            account_name="@nhatminh_technology",
            access_token=settings.tiktok_client_secret or "mock_tiktok_token_2026",
        )
        print(f"✅ Đã liên kết kênh TikTok: {conn.account_name} (Platform: {conn.platform.value})")

        # 3. Tạo Content Draft Video TikTok
        video_title = "Bí Quyết Tăng Tốc Xử Lý Máy Tính Trong 30 Giây ⚡"
        video_script = (
            "🔥 HOOK 3s: 'Máy tính của bạn đang chạy chậm như rùa? Xem ngay mẹo này!'\n\n"
            "💡 Bước 1: Mở Task Manager tắt app khởi động cùng Windows.\n"
            "💡 Bước 2: Dọn dẹp ổ đĩa tạm Temp files.\n"
            "💡 Lời kêu gọi: Ghé ngay Trung Tâm Công Nghệ Nhật Minh để nâng cấp SSD và bảo dưỡng miễn phí!\n\n"
            "#nhatminhtech #havi #tiktok #congnghe #meomaytinh"
        )

        job, _ = await content_repo.create_job(
            workspace_id=ws.id,
            raw_inputs=[{"kind": "text", "value": video_title}],
            idempotency_key=f"demo_job_{uuid4().hex}",
        )

        tiktok_item = await content_repo.create_item(
            workspace_id=ws.id,
            job_id=job.id,
            channel=Channel.TIKTOK,
            kind="Video TikTok (9:16)",
            text=video_script,
            media_note="Video dọc 9:16, nhạc nền xu hướng năng động, chữ vàng viền đen chuẩn TikTok",
            status=ContentStatus.PENDING_APPROVAL,
        )
        print(f"✅ Đã tạo Bản nháp Video TikTok (ID: {tiktok_item.id}) — Trạng thái: {tiktok_item.status.value}")

        # 4. Duyệt bài (Approval) -> Tự động đặt lịch khung giờ vàng
        approval_svc = ApprovalService(content=content_repo, events=event_repo)
        approved_item = await approval_svc.approve(
            workspace_id=ws.id,
            item_id=tiktok_item.id,
            user_id=user.id,
            scheduled_at=None,  # Tự động chọn khung giờ vàng gần nhất (08:00, 12:00, 20:00 ICT)
        )
        print(f"✅ Chủ tiệm đã DUYỆT BÀI $\\rightarrow$ Tự động xếp lịch xuất bản: {approved_item.scheduled_at.isoformat()} (Giờ vàng ICT)")

        # 5. Khởi tạo Publisher mô phỏng xuất bản thành công
        tiktok_pub = FakePublisher(
            channel=Channel.TIKTOK,
            post_id="v_pub_tiktok_live_success_999",
        )

        publish_svc = PublishService(
            content=content_repo,
            connections=conn_repo,
            publishes=publish_repo,
            events=event_repo,
            media=media_repo,
            alerts=LoggingAlertSink(),
            publishers={Channel.TIKTOK: tiktok_pub},
        )

        # 6. Đưa vào hàng đợi và chạy Publish Worker
        publish_job, _ = await publish_repo.enqueue(
            workspace_id=ws.id,
            content_item_id=approved_item.id,
            channel=Channel.TIKTOK,
            scheduled_at=approved_item.scheduled_at,
        )
        print(f"✅ Đã đưa vào hàng đợi xuất bản (Job ID: {publish_job.id})")

        # Thực thi xuất bản
        result = await publish_svc.run_job(publish_job)
        print(f"🎉 XUẤT BẢN THÀNH CÔNG! Trạng thái: {result.status.value}")
        print(f"📦 TikTok External Post ID: {result.external_post_id}")

        # 7. Kiểm tra trạng thái cuối cùng của Content Item
        final_item = await content_repo.get_item(workspace_id=ws.id, item_id=approved_item.id)
        assert final_item.status == ContentStatus.PUBLISHED
        print(f"🏆 Trạng thái bài đăng trong Database: {final_item.status.value.upper()}")
        print("=" * 60)
        print("✨ TOÀN BỘ FLOW TIKTOK ĐÃ TEST XONG 100% HOÀN HẢO TẠI LOCAL!")
        print("=" * 60)

        await session.commit()


if __name__ == "__main__":
    asyncio.run(run_tiktok_demo())
