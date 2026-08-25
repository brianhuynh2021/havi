"""Use case cho video: **tải clip lên → duyệt → đăng**. Không dựng, không sửa.

Havi cố tình không phải công cụ biên tập. Chủ tiệm đã có CapCut và đã quen dùng;
thứ họ không có là một đường đăng đáng tin — đăng đúng giờ, biết chắc bài đã lên,
và không bao giờ đăng trùng. Toàn bộ giá trị của luồng này nằm ở đó.

Nên service này chỉ làm hai việc:

1. **Nhận clip và nói ngay nó đăng được hay không.** Kiểm ràng buộc kênh tại
   thời điểm upload, lúc chủ tiệm còn đứng ở tiệm và còn quay lại được — chứ
   không phải lúc scheduler chạy vào 8 giờ tối và đã lỡ giờ.
2. **Giữ trạng thái** để `VideoPublishService` có chỗ bám mà đối soát với
   Facebook. Việc đăng và xác minh nằm ở đó, không nằm ở đây.
"""

import logging
from uuid import UUID

from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.video_post_repository import VideoPostRepository
from core.enums import Channel, MediaStatus, MediaType, VideoPostStatus
from domain.models.video_post import VideoPost
from domain.policies.video_constraints import check_video_for_channel, eligible_channels
from domain.ports.media import VideoMetadata

logger = logging.getLogger("havi.video_post")


class VideoPostNotFound(Exception):
    """Không tìm thấy video post trong workspace này."""


class ClipNotPublishable(Exception):
    """Clip không đáp ứng ràng buộc của kênh đích.

    Mang theo cả danh sách lý do chứ không chỉ câu đầu tiên: chủ tiệm sửa được
    một lượt (quay dọc lại *và* cắt ngắn) thay vì tải lên ba lần để phát hiện
    ba lỗi.
    """

    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        super().__init__("; ".join(reasons))


class VideoPostService:
    def __init__(
        self,
        posts: VideoPostRepository,
        media: MediaRepository,
    ) -> None:
        self._posts = posts
        self._media = media

    async def create_from_upload(
        self,
        *,
        workspace_id: UUID,
        source_media_id: UUID,
        caption: str = "",
        channel: Channel = Channel.REELS,
    ) -> VideoPost:
        """Biến một clip đã upload xong thành một bài chờ duyệt.

        Ném `ClipNotPublishable` ngay tại request thay vì tạo bản ghi rồi để nó
        hỏng ở worker: người dùng biết ngay tại chỗ, và Havi không tích lũy một
        đống job `failed` mà không ai đọc.
        """
        asset = await self._media.get(workspace_id=workspace_id, asset_id=source_media_id)
        if asset is None:
            raise VideoPostNotFound(f"Không tìm thấy clip {source_media_id}")
        if asset.type is not MediaType.VIDEO:
            raise ClipNotPublishable(["File này không phải video"])
        if asset.status is MediaStatus.PENDING:
            raise ClipNotPublishable(
                ["Clip chưa tải xong. Đợi vài giây rồi thử lại giúp bạn nhé."]
            )

        reasons = check_video_for_channel(_metadata_of(asset), channel)
        if reasons:
            raise ClipNotPublishable(reasons)

        post = await self._posts.create(
            workspace_id=workspace_id,
            source_media_id=source_media_id,
            source_object_key=asset.object_key,
            caption=caption,
            channel=channel,
        )
        logger.info(
            "video_post.created post_id=%s workspace_id=%s channel=%s",
            post.id,
            workspace_id,
            channel.value,
        )
        return post

    async def get(self, *, workspace_id: UUID, post_id: UUID) -> VideoPost:
        post = await self._posts.get(workspace_id=workspace_id, post_id=post_id)
        if not post:
            raise VideoPostNotFound(f"Không tìm thấy video {post_id}")
        return post

    async def list(
        self,
        *,
        workspace_id: UUID,
        status: VideoPostStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[VideoPost], int]:
        return await self._posts.list_for_workspace(
            workspace_id=workspace_id, status=status, limit=limit, offset=offset
        )

    async def update_caption(
        self, *, workspace_id: UUID, post_id: UUID, caption: str
    ) -> VideoPost:
        """Sửa caption — chỉ được phép trước khi duyệt.

        Sau `APPROVED` thì caption có thể đã đi cùng bytes sang Facebook; sửa ở
        Havi lúc đó chỉ làm bản ghi khác với thứ đang hiện trên Trang.
        """
        post = await self.get(workspace_id=workspace_id, post_id=post_id)
        if post.status is not VideoPostStatus.READY_FOR_REVIEW:
            raise ClipNotPublishable(
                ["Video đã duyệt hoặc đã gửi đăng — không sửa caption ở Havi được nữa."]
            )
        post.caption = caption
        return post

    async def cancel(self, *, workspace_id: UUID, post_id: UUID) -> bool:
        return await self._posts.cancel(workspace_id=workspace_id, post_id=post_id)

    async def channels_for_clip(
        self, *, workspace_id: UUID, source_media_id: UUID
    ) -> list[Channel]:
        """Clip này đăng được lên kênh nào — để UI hiện ngay sau khi upload."""
        asset = await self._media.get(workspace_id=workspace_id, asset_id=source_media_id)
        if asset is None:
            raise VideoPostNotFound(f"Không tìm thấy clip {source_media_id}")
        return eligible_channels(_metadata_of(asset))


def _metadata_of(asset) -> VideoMetadata | None:  # noqa: ANN001 — MediaAsset, tránh vòng import
    """`None` khi probe chưa chạy hoặc đã hỏng.

    Trả `None` thay vì dựng một `VideoMetadata` với số 0: `check_video_for_channel`
    coi `None` là "chưa biết nên chưa kết luận được", còn số 0 thì trông như một
    phép đo thật và sẽ sinh ra lý do từ chối sai.

    Kiểm cả `width`/`height` chứ không chỉ `duration`: từ khi ràng buộc khung
    hình so bằng số, kích thước pixel mới là thứ quyết định — thiếu nó thì không
    tính được tỉ lệ, và chia cho 0 là cách biến một lần probe hỏng thành một
    exception ở giữa luồng upload.
    """
    if asset.duration_seconds is None or not asset.width or not asset.height:
        return None
    return VideoMetadata(
        duration_seconds=asset.duration_seconds,
        width=asset.width or 0,
        height=asset.height or 0,
        aspect_ratio=asset.aspect_ratio,
        has_audio=bool(asset.has_audio),
    )
