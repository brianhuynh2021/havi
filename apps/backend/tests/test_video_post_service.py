"""Nhận clip → kiểm ràng buộc kênh → tạo bài chờ duyệt.

Bộ test này bảo vệ một luật: **clip sai bị chặn ngay lúc upload, không phải lúc
đăng.** Chủ tiệm quay clip rồi hẹn đăng tối thứ Bảy; nếu cái sai (quay ngang,
dài quá) chỉ lộ ra lúc scheduler chạy thì đã lỡ giờ và không quay lại được nữa.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.video_post_repository import VideoPostRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.video_post_service import (
    ClipNotPublishable,
    VideoPostNotFound,
    VideoPostService,
)
from core.enums import Channel, Industry, MediaStatus, MediaType, VideoPostStatus


async def _workspace(db_session: AsyncSession, tag: str):
    user = await UserRepository(db_session).create(
        email=f"{tag}_{uuid4().hex[:6]}@havi.vn", name="Chủ Tiệm", password_hash="h"
    )
    return await WorkspaceRepository(db_session).create(
        name=f"Tiệm {tag}", industry=Industry.SPA, owner_user_id=user.id
    )


async def _clip(
    db_session: AsyncSession,
    workspace_id,
    *,
    duration=20.0,
    aspect="9:16",
    width=1080,
    height=1920,
    has_audio=True,
    media_type=MediaType.VIDEO,
    status=MediaStatus.RAW,
):
    """Một clip đã upload xong, với đúng thông số probe đọc được."""
    repo = MediaRepository(db_session)
    asset = await repo.create(
        workspace_id=workspace_id,
        filename="clip.mp4",
        content_type="video/mp4",
        type=media_type,
        object_key=f"workspaces/{workspace_id}/media/{uuid4().hex}.mp4",
    )
    asset.status = status
    asset.duration_seconds = duration
    asset.aspect_ratio = aspect
    asset.width = width
    asset.height = height
    asset.has_audio = has_audio
    await db_session.flush()
    return asset


def _service(db_session: AsyncSession) -> VideoPostService:
    return VideoPostService(
        posts=VideoPostRepository(db_session), media=MediaRepository(db_session)
    )


@pytest.mark.asyncio
async def test_clip_hop_le_vao_thang_cho_duyet(db_session: AsyncSession):
    """Không có bước dựng nào ở giữa — clip lên là chờ người duyệt ngay."""
    ws = await _workspace(db_session, "ok")
    clip = await _clip(db_session, ws.id)

    post = await _service(db_session).create_from_upload(
        workspace_id=ws.id, source_media_id=clip.id, caption="Ưu đãi tháng 8"
    )

    assert post.status is VideoPostStatus.READY_FOR_REVIEW
    assert post.caption == "Ưu đãi tháng 8"
    assert post.channel is Channel.REELS
    # Key chốt ngay lúc tạo: lúc đăng cần đúng một thứ — file nào.
    assert post.source_object_key == clip.object_key


@pytest.mark.asyncio
async def test_clip_quay_ngang_bi_chan_ngay_luc_upload(db_session: AsyncSession):
    ws = await _workspace(db_session, "landscape")
    clip = await _clip(db_session, ws.id, aspect="16:9", width=1920, height=1080)

    with pytest.raises(ClipNotPublishable) as exc:
        await _service(db_session).create_from_upload(
            workspace_id=ws.id, source_media_id=clip.id
        )
    assert any("9:16" in reason for reason in exc.value.reasons)


@pytest.mark.asyncio
async def test_clip_dai_qua_gioi_han_reels_bi_chan(db_session: AsyncSession):
    ws = await _workspace(db_session, "toolong")
    clip = await _clip(db_session, ws.id, duration=200.0)

    with pytest.raises(ClipNotPublishable) as exc:
        await _service(db_session).create_from_upload(
            workspace_id=ws.id, source_media_id=clip.id
        )
    assert any("90" in reason for reason in exc.value.reasons)


@pytest.mark.asyncio
async def test_tra_ve_het_ly_do_mot_luot_chu_khong_chi_ly_do_dau(db_session: AsyncSession):
    """Chủ tiệm sửa được một lượt, thay vì tải lên ba lần để phát hiện ba lỗi."""
    ws = await _workspace(db_session, "manyreasons")
    clip = await _clip(db_session, ws.id, aspect="16:9", duration=1.0, width=1920, height=1080)

    with pytest.raises(ClipNotPublishable) as exc:
        await _service(db_session).create_from_upload(
            workspace_id=ws.id, source_media_id=clip.id, channel=Channel.REELS
        )
    assert len(exc.value.reasons) >= 2


@pytest.mark.asyncio
async def test_chua_probe_duoc_thi_tu_choi_ro_rang_chu_khong_doan_bua(
    db_session: AsyncSession,
):
    """Thông số NULL = chưa biết. Đoán bừa là cách một file hỏng lọt lên Trang."""
    ws = await _workspace(db_session, "noprobe")
    clip = await _clip(db_session, ws.id)
    clip.duration_seconds = None
    clip.aspect_ratio = None
    await db_session.flush()

    with pytest.raises(ClipNotPublishable) as exc:
        await _service(db_session).create_from_upload(
            workspace_id=ws.id, source_media_id=clip.id
        )
    assert any("thông số" in reason.lower() for reason in exc.value.reasons)


@pytest.mark.asyncio
async def test_clip_chua_tai_xong_thi_bao_doi_chu_khong_bao_loi_ky_thuat(
    db_session: AsyncSession,
):
    ws = await _workspace(db_session, "pending")
    clip = await _clip(db_session, ws.id, status=MediaStatus.PENDING)

    with pytest.raises(ClipNotPublishable) as exc:
        await _service(db_session).create_from_upload(
            workspace_id=ws.id, source_media_id=clip.id
        )
    assert "chưa tải xong" in str(exc.value)


@pytest.mark.asyncio
async def test_file_anh_khong_phai_video_thi_tu_choi(db_session: AsyncSession):
    ws = await _workspace(db_session, "image")
    clip = await _clip(db_session, ws.id, media_type=MediaType.IMAGE)

    with pytest.raises(ClipNotPublishable):
        await _service(db_session).create_from_upload(
            workspace_id=ws.id, source_media_id=clip.id
        )


@pytest.mark.asyncio
async def test_clip_cua_workspace_khac_thi_khong_thay(db_session: AsyncSession):
    """Cách ly tenant: id đoán được thì cũng không đọc được clip của tiệm khác."""
    ws_a = await _workspace(db_session, "tenanta")
    ws_b = await _workspace(db_session, "tenantb")
    clip = await _clip(db_session, ws_b.id)

    with pytest.raises(VideoPostNotFound):
        await _service(db_session).create_from_upload(
            workspace_id=ws_a.id, source_media_id=clip.id
        )


@pytest.mark.asyncio
async def test_sua_caption_sau_khi_duyet_bi_chan(db_session: AsyncSession):
    """Sau khi duyệt, caption có thể đã đi cùng bytes — sửa ở Havi là nói dối."""
    ws = await _workspace(db_session, "caption")
    clip = await _clip(db_session, ws.id)
    service = _service(db_session)
    post = await service.create_from_upload(
        workspace_id=ws.id, source_media_id=clip.id, caption="bản đầu"
    )

    updated = await service.update_caption(
        workspace_id=ws.id, post_id=post.id, caption="bản sửa"
    )
    assert updated.caption == "bản sửa"

    post.status = VideoPostStatus.APPROVED
    await db_session.flush()
    with pytest.raises(ClipNotPublishable):
        await service.update_caption(
            workspace_id=ws.id, post_id=post.id, caption="sửa lần nữa"
        )


@pytest.mark.asyncio
async def test_khong_huy_duoc_video_da_gui_di(db_session: AsyncSession):
    """Huỷ ở Havi không gỡ bài khỏi Trang — cho huỷ lúc đó là nói dối chủ tiệm."""
    ws = await _workspace(db_session, "cancel")
    clip = await _clip(db_session, ws.id)
    service = _service(db_session)
    post = await service.create_from_upload(workspace_id=ws.id, source_media_id=clip.id)

    post.status = VideoPostStatus.PUBLISHING
    await db_session.flush()

    assert await service.cancel(workspace_id=ws.id, post_id=post.id) is False


@pytest.mark.asyncio
async def test_goi_y_kenh_dang_duoc_ngay_sau_khi_upload(db_session: AsyncSession):
    """Clip 9:16 70 giây có tiếng: Reels và TikTok nhận, Shorts (tối đa 60s) thì không."""
    ws = await _workspace(db_session, "eligible")
    clip = await _clip(db_session, ws.id, duration=70.0)

    channels = await _service(db_session).channels_for_clip(
        workspace_id=ws.id, source_media_id=clip.id
    )
    assert Channel.REELS in channels
    assert Channel.TIKTOK in channels
    assert Channel.YOUTUBE not in channels
