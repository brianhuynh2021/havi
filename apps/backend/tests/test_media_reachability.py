"""URL media không tải được từ Internet phải bị chặn TRƯỚC khi gửi cho nền tảng.

Nhóm test này sinh ra từ hai job nằm trong dead-letter thật::

    [100] (#100) url should represent a valid URL
    [6000] There was a problem uploading your video file.

Cả hai cùng một gốc: `HAVI_MEDIA_PUBLIC_URL=http://localhost:9000`. Bài đăng
hoàn toàn bình thường, chỉ có điều `localhost` gửi cho Facebook nghĩa là *máy của
Facebook*. Điều đáng sửa không chỉ là cấu hình — mà là việc Havi im lặng gửi đi
một đường link nó tự biết là vô nghĩa, rồi để nền tảng trả về một mã số không
nói gì về nguyên nhân.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.publish_repository import PublishRepository
from adapters.publishers.fake import FakePublisher
from core.enums import Channel, Platform, PublishFailureKind, PublishStatus
from domain.models.workspace import Workspace
from domain.policies.media_reachability import unreachable_reason

pytestmark = pytest.mark.anyio


class TestLuatURLCongKhai:
    """Luật thuần tuý — không chạm database, không gọi mạng."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost:9000/havi-media/clip.mp4",
            "http://127.0.0.1:9000/havi-media/clip.mp4",
            "http://[::1]:9000/havi-media/clip.mp4",
            "http://192.168.1.202:9000/havi-media/anh.jpg",
            "http://10.0.0.5/anh.jpg",
            "http://172.16.3.9/anh.jpg",
            "http://minio:9000/havi-media/anh.jpg",  # tên service Docker Compose
            "http://macbook.local/anh.jpg",
            "blob:http://localhost:3000/9f2c-4a1e",  # URL của trình duyệt
            "file:///Users/huynh/clip.mp4",
            "data:image/png;base64,iVBORw0KGgo=",
        ],
    )
    def test_chan_moi_dang_link_chi_mo_duoc_o_may_nay(self, url: str):
        assert unreachable_reason(url) is not None

    @pytest.mark.parametrize(
        "url",
        [
            "https://media.havi.vn/havi-media/clip.mp4",
            "https://havi-media.s3.ap-southeast-1.amazonaws.com/clip.mp4?X-Amz-Signature=abc",
            "http://203.162.4.1/anh.jpg",  # IP công khai, vẫn hợp lệ
        ],
    )
    def test_cho_qua_link_that_su_cong_khai(self, url: str):
        assert unreachable_reason(url) is None

    def test_ly_do_tra_ve_bang_tieng_viet_doc_duoc(self):
        """`failure_detail` là thứ người vận hành đọc, không phải mã lỗi để tra."""
        reason = unreachable_reason("http://localhost:9000/clip.mp4")
        assert reason is not None
        assert "localhost" in reason
        # Không phải một chuỗi kiểu `ERR_LOCAL_HOST` hay tên hàm Python.
        assert " " in reason and reason.lower() == reason[:1].lower() + reason[1:]


class TestChanTruocKhiGuiChoNenTang:
    """Đường đăng bài thật: job phải chết ở Havi, không chết ở Facebook."""

    async def _workspace(self, session: AsyncSession) -> Workspace:
        from core.enums import Industry
        from domain.models.user import User

        owner = User(email=f"{uuid.uuid4().hex[:10]}@spa.vn", name="Chị Hương")
        session.add(owner)
        await session.flush()
        ws = Workspace(name="Spa An Nhiên", industry=Industry.SPA, owner_user_id=owner.id)
        session.add(ws)
        await session.flush()
        return ws

    async def _run(self, session: AsyncSession, *, media_url: str, publisher: FakePublisher):
        from adapters.persistence.connection_repository import ConnectionRepository
        from adapters.persistence.content_repository import ContentRepository
        from application.services.publish_service import PublishService
        from core.enums import ContentStatus
        from domain.models.content import ContentItem

        ws = await self._workspace(session)
        await ConnectionRepository(session).upsert(
            workspace_id=ws.id,
            platform=Platform.FACEBOOK,
            access_token="page-token",
            external_account_id="page_1",
        )
        at = datetime.now(UTC) - timedelta(minutes=1)
        item = ContentItem(
            workspace_id=ws.id,
            job_id=None,
            channel=Channel.FACEBOOK_PAGE,
            kind="Bài ảnh",
            text="Ưu đãi gội đầu thảo dược",
            media_url=media_url,
            status=ContentStatus.SCHEDULED,
            scheduled_at=at,
        )
        session.add(item)
        await session.flush()

        publishes = PublishRepository(session)
        job, _ = await publishes.enqueue(
            workspace_id=ws.id,
            content_item_id=item.id,
            channel=Channel.FACEBOOK_PAGE,
            scheduled_at=at,
        )
        service = PublishService(
            content=ContentRepository(session),
            connections=ConnectionRepository(session),
            publishes=publishes,
            events=EventLogRepository(session),
            publishers={Channel.FACEBOOK_PAGE: publisher},
        )
        return await service.run_job(job)

    async def test_link_localhost_khong_bao_gio_toi_tay_facebook(self, db_session: AsyncSession):
        """Điểm quan trọng nhất: adapter KHÔNG được gọi.

        Gửi đi rồi mới hỏng thì Facebook đã nhận request, và ta không còn chắc
        chắn được là bài không lên — đúng loại mơ hồ mà `AmbiguousPublishError`
        sinh ra để xử lý. Chặn ở nhà thì không có mơ hồ nào cả.
        """
        publisher = FakePublisher()
        job = await self._run(
            db_session,
            media_url="http://localhost:9000/havi-media/clip.mp4",
            publisher=publisher,
        )

        assert publisher.calls == []
        assert job.status is PublishStatus.DEAD_LETTER

    async def test_bao_dung_nguyen_nhan_thay_vi_do_loi_cho_bai_dang(self, db_session: AsyncSession):
        """`(#100) url should represent a valid URL` khiến người đọc đi sửa bài.

        Bài không có lỗi. Thông báo phải nói ra điều đó, và nói luôn chỗ cần sửa.
        """
        job = await self._run(
            db_session,
            media_url="http://localhost:9000/havi-media/clip.mp4",
            publisher=FakePublisher(),
        )

        detail = job.failure_detail or ""
        assert "Bài đăng không có lỗi" in detail
        assert "HAVI_MEDIA_PUBLIC_URL" in detail
        assert job.failure_kind is PublishFailureKind.VALIDATION_PERMANENT

    async def test_khong_retry_vi_thu_lai_khong_the_lam_localhost_thanh_cong_khai(
        self, db_session: AsyncSession
    ):
        """Cấu hình sai thì thử lại mười lần vẫn sai — đây là lỗi vĩnh viễn."""
        job = await self._run(
            db_session,
            media_url="http://localhost:9000/havi-media/clip.mp4",
            publisher=FakePublisher(),
        )
        assert job.status is PublishStatus.DEAD_LETTER

    async def test_link_cong_khai_van_dang_binh_thuong(self, db_session: AsyncSession):
        """Chốt chặn không được rộng tay tới mức chặn nhầm link thật."""
        publisher = FakePublisher()
        job = await self._run(
            db_session,
            media_url="https://media.havi.vn/havi-media/clip.mp4",
            publisher=publisher,
        )

        assert len(publisher.calls) == 1
        assert job.status is PublishStatus.SUCCEEDED
