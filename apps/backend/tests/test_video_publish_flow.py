"""Duyệt → đăng → xác minh, và mọi cách nó có thể hỏng.

Bộ test này bảo vệ hai luật đắt nhất của sản phẩm:

1. Không có đường nào tới `PUBLISHED` mà không đọc lại nền tảng.
2. Mất dấu thì đối soát, không gửi lại — gửi lại là hai Reels trên Trang khách.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.user_repository import UserRepository
from adapters.persistence.video_post_repository import VideoPostRepository
from adapters.persistence.video_publish_repository import (
    DuplicatePublishAttempt,
    VideoPublishRepository,
)
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.video_publish_service import (
    ChannelNotConnected,
    VideoNotReadyForPublish,
    VideoPublishService,
)
from core.enums import (
    Channel,
    ConnectionStatus,
    Industry,
    VideoPostStatus,
    VideoPublishAttemptStatus,
)
from domain.ports.publisher import (
    AmbiguousPublishError,
    PublishResult,
    ReelStatus,
    ValidationPublishError,
)


class FakeConnection:
    def __init__(self, status=ConnectionStatus.CONNECTED, page_id="page-1"):
        self.status = status
        self.external_account_id = page_id


class FakeConnections:
    def __init__(self, connection=None):
        self._connection = connection if connection is not None else FakeConnection()

    async def get(self, *, workspace_id, platform):
        return self._connection

    def read_access_token(self, connection) -> str:
        return "tok-123"


class FakePublisher:
    """Publisher điều khiển được: mỗi test khai đúng cách Facebook hành xử."""

    def __init__(self, *, publish_result=None, publish_error=None, verify_results=None):
        self._publish_result = publish_result or PublishResult(
            external_post_id="vid-777", published_at=datetime.now(UTC)
        )
        self._publish_error = publish_error
        self._verify_results = list(verify_results or [ReelStatus("vid-777", "published")])
        self.publish_calls = 0
        self.verify_calls = 0

    async def publish(self, request, *, access_token):
        self.publish_calls += 1
        if self._publish_error:
            raise self._publish_error
        return self._publish_result

    async def verify_reel(self, video_id, *, access_token):
        self.verify_calls += 1
        if len(self._verify_results) > 1:
            return self._verify_results.pop(0)
        return self._verify_results[0]


async def _ready_post(db_session: AsyncSession, tag: str, **overrides):
    """Một clip đã upload xong, đã qua kiểm ràng buộc kênh, đang chờ duyệt."""
    user = await UserRepository(db_session).create(
        email=f"{tag}_{uuid4().hex[:6]}@havi.vn", name="Chủ Tiệm", password_hash="h"
    )
    ws = await WorkspaceRepository(db_session).create(
        name=f"Tiệm {tag}", industry=Industry.EDUCATION, owner_user_id=user.id
    )
    repo = VideoPostRepository(db_session)
    post = await repo.create(
        workspace_id=ws.id,
        source_media_id=None,
        source_object_key=f"workspaces/{ws.id}/media/clip.mp4",
        caption="Clip lớp Robot",
    )
    if "status" in overrides:
        post.status = overrides["status"]
    await db_session.flush()
    return ws, post, repo


def _service(db_session, publisher, connections=None):
    return VideoPublishService(
        posts=VideoPostRepository(db_session),
        attempts=VideoPublishRepository(db_session),
        connections=connections or FakeConnections(),
        publisher=publisher,
        signed_url_for=lambda post: "https://storage.havi.vn/signed/clip.mp4",
    )


# ------------------------------------------------------------------ duyệt


@pytest.mark.asyncio
async def test_da_gui_di_roi_thi_khong_duyet_lai(db_session: AsyncSession):
    """Duyệt lại một video đã gửi = hai Reels trên Trang khách."""
    ws, post, _ = await _ready_post(db_session, "resent", status=VideoPostStatus.PUBLISHED)
    service = _service(db_session, FakePublisher())
    with pytest.raises(VideoNotReadyForPublish) as exc:
        await service.approve(workspace_id=ws.id, post_id=post.id)
    assert "đăng trùng" in str(exc.value)


@pytest.mark.asyncio
async def test_chua_noi_trang_thi_khong_duyet_duoc(db_session: AsyncSession):
    """Bắt lỗi kết nối lúc bấm duyệt, không đợi tới worker — ở worker không ai đọc."""
    ws, post, _ = await _ready_post(db_session, "approvenoconn")
    service = _service(
        db_session,
        FakePublisher(),
        connections=FakeConnections(FakeConnection(status=ConnectionStatus.REVOKED)),
    )
    with pytest.raises(ChannelNotConnected):
        await service.approve(workspace_id=ws.id, post_id=post.id)
    assert post.status == VideoPostStatus.READY_FOR_REVIEW


@pytest.mark.asyncio
async def test_video_da_huy_khong_duyet_lai_duoc(db_session: AsyncSession):
    """Nhảy cóc trạng thái bị chặn ở state machine, không phải ở một cái if."""
    from domain.policies.video_job_state import InvalidStateTransition

    ws, post, _ = await _ready_post(db_session, "cancelled", status=VideoPostStatus.CANCELLED)
    service = _service(db_session, FakePublisher())
    with pytest.raises(InvalidStateTransition):
        await service.approve(workspace_id=ws.id, post_id=post.id)


# ------------------------------------------------------------------- đăng


@pytest.mark.asyncio
async def test_duong_thanh_cong_chi_toi_published_sau_khi_doc_lai_facebook(
    db_session: AsyncSession,
):
    ws, post, repo = await _ready_post(db_session, "ok")
    publisher = FakePublisher()
    service = _service(db_session, publisher)

    await service.approve(workspace_id=ws.id, post_id=post.id)
    assert post.status == VideoPostStatus.APPROVED

    outcome = await service.publish(workspace_id=ws.id, post_id=post.id)

    assert outcome.post.status == VideoPostStatus.PUBLISHED
    assert outcome.external_post_id == "vid-777"
    assert publisher.verify_calls == 1, "phải đọc lại nền tảng trước khi kết luận đã đăng"
    assert outcome.attempt.status == VideoPublishAttemptStatus.PUBLISHED

    saved = await repo.get(workspace_id=ws.id, post_id=post.id)
    assert saved.status == VideoPostStatus.PUBLISHED


@pytest.mark.asyncio
async def test_chua_duyet_thi_khong_dang_duoc(db_session: AsyncSession):
    ws, post, _ = await _ready_post(db_session, "notapproved")
    publisher = FakePublisher()
    service = _service(db_session, publisher)

    with pytest.raises(VideoNotReadyForPublish):
        await service.publish(workspace_id=ws.id, post_id=post.id)
    assert publisher.publish_calls == 0


@pytest.mark.asyncio
async def test_ket_noi_mat_giua_luc_duyet_va_luc_dang_thi_khong_gui_di(
    db_session: AsyncSession,
):
    """Tình huống thật: token Facebook hết hạn sau khi chủ tiệm đã bấm duyệt.

    Kiểm lại ở `publish` chứ không tin kết quả kiểm lúc `approve`: giữa hai thời
    điểm đó có thể là hàng giờ, và một token đã hết hạn thì gửi đi chỉ tốn băng
    thông rồi nhận về một lỗi mơ hồ.
    """
    ws, post, _ = await _ready_post(db_session, "noconn")
    publisher = FakePublisher()
    connections = FakeConnections()
    service = _service(db_session, publisher, connections=connections)

    await service.approve(workspace_id=ws.id, post_id=post.id)

    connections._connection = FakeConnection(status=ConnectionStatus.REVOKED)
    with pytest.raises(ChannelNotConnected):
        await service.publish(workspace_id=ws.id, post_id=post.id)
    assert publisher.publish_calls == 0


@pytest.mark.asyncio
async def test_facebook_tu_choi_noi_dung_thi_that_bai_khong_treo(db_session: AsyncSession):
    ws, post, _ = await _ready_post(db_session, "rejected")
    publisher = FakePublisher(
        publish_error=ValidationPublishError(Channel.REELS, "Video vi phạm chính sách")
    )
    service = _service(db_session, publisher)
    await service.approve(workspace_id=ws.id, post_id=post.id)

    outcome = await service.publish(workspace_id=ws.id, post_id=post.id)
    assert outcome.post.status == VideoPostStatus.FAILED
    assert outcome.attempt.status == VideoPublishAttemptStatus.FAILED
    assert publisher.verify_calls == 0


@pytest.mark.asyncio
async def test_facebook_van_dang_xu_ly_thi_chua_duoc_bao_da_dang(db_session: AsyncSession):
    """`finish` trả 200 không có nghĩa là video đã lên Trang."""
    ws, post, _ = await _ready_post(db_session, "processing")
    publisher = FakePublisher(verify_results=[ReelStatus("vid-777", "in_progress")])
    service = _service(db_session, publisher)
    await service.approve(workspace_id=ws.id, post_id=post.id)

    outcome = await service.publish(workspace_id=ws.id, post_id=post.id)
    assert outcome.post.status == VideoPostStatus.PENDING_RECONCILIATION
    assert outcome.attempt.status == VideoPublishAttemptStatus.AMBIGUOUS


@pytest.mark.asyncio
async def test_facebook_bao_loi_sau_khi_nhan_thi_video_that_bai(db_session: AsyncSession):
    ws, post, _ = await _ready_post(db_session, "fberror")
    publisher = FakePublisher(
        verify_results=[ReelStatus("vid-777", "error", error_message="Định dạng không hợp lệ")]
    )
    service = _service(db_session, publisher)
    await service.approve(workspace_id=ws.id, post_id=post.id)

    outcome = await service.publish(workspace_id=ws.id, post_id=post.id)
    assert outcome.post.status == VideoPostStatus.FAILED
    assert "Định dạng không hợp lệ" in outcome.post.error_message


# --------------------------------------------------------- chống đăng trùng


@pytest.mark.asyncio
async def test_bam_dang_hai_lan_khong_tao_hai_bai(db_session: AsyncSession):
    """Lớp chặn nằm ở ràng buộc unique của Postgres, không ở một cái if."""
    ws, post, _ = await _ready_post(db_session, "double")
    publisher = FakePublisher()
    service = _service(db_session, publisher)
    await service.approve(workspace_id=ws.id, post_id=post.id)

    first = await service.publish(workspace_id=ws.id, post_id=post.id)
    assert first.post.status == VideoPostStatus.PUBLISHED
    assert publisher.publish_calls == 1

    with pytest.raises(VideoNotReadyForPublish) as exc:
        await service.publish(workspace_id=ws.id, post_id=post.id)
    assert "đăng trùng" in str(exc.value)
    assert publisher.publish_calls == 1, "lần bấm thứ hai không được chạm tới Facebook"


@pytest.mark.asyncio
async def test_rang_buoc_postgres_chan_lan_gui_thu_hai_khi_lan_dau_con_pending(
    db_session: AsyncSession,
):
    ws, post, _ = await _ready_post(db_session, "pgguard")
    attempts = VideoPublishRepository(db_session)
    await attempts.start_attempt(
        workspace_id=ws.id,
        video_post_id=post.id,
        channel=Channel.REELS,
        idempotency_key="key-1",
    )
    with pytest.raises(DuplicatePublishAttempt):
        await attempts.start_attempt(
            workspace_id=ws.id,
            video_post_id=post.id,
            channel=Channel.REELS,
            idempotency_key="key-2",
        )


# ------------------------------------------------------------- đối soát


@pytest.mark.asyncio
async def test_mat_dau_sau_khi_gui_thi_khong_gui_lai_ma_di_doi_soat(
    db_session: AsyncSession,
):
    ws, post, _ = await _ready_post(db_session, "ambiguous")
    publisher = FakePublisher(
        publish_error=AmbiguousPublishError(Channel.REELS, "timeout sau khi upload")
    )
    service = _service(db_session, publisher)
    await service.approve(workspace_id=ws.id, post_id=post.id)

    outcome = await service.publish(workspace_id=ws.id, post_id=post.id)
    assert outcome.post.status == VideoPostStatus.PENDING_RECONCILIATION
    assert outcome.attempt.status == VideoPublishAttemptStatus.AMBIGUOUS
    # Không có đường nào từ đây quay lại PUBLISHING.
    from domain.policies.video_job_state import can_transition

    assert not can_transition(
        VideoPostStatus.PENDING_RECONCILIATION, VideoPostStatus.PUBLISHING
    )


@pytest.mark.asyncio
async def test_doi_soat_tim_thay_bai_da_len_trang_thi_ket_luan_da_dang(
    db_session: AsyncSession,
):
    ws, post, _ = await _ready_post(db_session, "reconok")
    publisher = FakePublisher(
        publish_error=AmbiguousPublishError(Channel.REELS, "timeout"),
    )
    service = _service(db_session, publisher)
    await service.approve(workspace_id=ws.id, post_id=post.id)
    outcome = await service.publish(workspace_id=ws.id, post_id=post.id)

    attempt = outcome.attempt
    attempt.external_post_id = "vid-999"
    await db_session.flush()

    publisher._verify_results = [
        ReelStatus("vid-999", "published", permalink_url="https://fb.com/reel/999")
    ]
    result = await service.reconcile(workspace_id=ws.id, attempt=attempt)

    assert result.post.status == VideoPostStatus.PUBLISHED
    assert result.external_post_id == "vid-999"
    assert result.permalink_url == "https://fb.com/reel/999"
    assert publisher.publish_calls == 1, "đối soát không được gửi lại"


@pytest.mark.asyncio
async def test_doi_soat_khong_co_ma_bai_thi_dung_han_cho_nguoi_that_xem(
    db_session: AsyncSession,
):
    """Dò danh sách video của Trang là cách dễ nhầm sang video khác nhất."""
    ws, post, _ = await _ready_post(db_session, "noid")
    publisher = FakePublisher(publish_error=AmbiguousPublishError(Channel.REELS, "timeout"))
    service = _service(db_session, publisher)
    await service.approve(workspace_id=ws.id, post_id=post.id)
    outcome = await service.publish(workspace_id=ws.id, post_id=post.id)

    attempt = outcome.attempt
    attempt.external_post_id = None
    await db_session.flush()

    result = await service.reconcile(workspace_id=ws.id, attempt=attempt)
    assert result.post.status == VideoPostStatus.FAILED_PERMANENT
    assert publisher.verify_calls == 0
