"""Video đăng được lên kênh nào — kiểm ngay lúc upload, không đợi tới lúc đăng.

Vì sao kiểm sớm: chủ tiệm quay clip bằng điện thoại rồi lên lịch đăng tối thứ
Bảy. Nếu ràng buộc chỉ được kiểm lúc scheduler gọi API nền tảng, thì cái sai
(quay ngang, dài quá, không có tiếng) chỉ lộ ra sau khi đã lỡ giờ đăng — và lúc
đó không sửa được nữa. Biết ngay lúc upload thì còn kịp quay lại.

Đây là domain policy thuần: không I/O, không SDK, chỉ số liệu vào và kết luận ra.
Con số lấy từ tài liệu công khai của từng nền tảng và sẽ lệch theo thời gian —
sửa ở đúng một chỗ này, và `VideoRequirement` mang theo lời giải thích để UI nói
được cho chủ tiệm bằng tiếng Việt thay vì hiện mã lỗi.
"""

from dataclasses import dataclass

from core.enums import Channel
from domain.ports.media import VideoMetadata


@dataclass(frozen=True)
class VideoRequirement:
    """Ràng buộc video của một kênh."""

    #: Khung hình chấp nhận được. Rỗng = kênh không kén.
    aspect_ratios: frozenset[str]
    min_duration_seconds: float
    max_duration_seconds: float
    requires_audio: bool
    label: str


#: Chỉ khai cho kênh video. Kênh ảnh/text không có mặt ở đây, và
#: `check_video_for_channel` coi kênh không khai là không ràng buộc.
VIDEO_REQUIREMENTS: dict[Channel, VideoRequirement] = {
    Channel.REELS: VideoRequirement(
        aspect_ratios=frozenset({"9:16"}),
        min_duration_seconds=3,
        max_duration_seconds=90,
        requires_audio=False,
        label="Facebook Reels",
    ),
    Channel.TIKTOK: VideoRequirement(
        aspect_ratios=frozenset({"9:16", "1:1"}),
        min_duration_seconds=3,
        max_duration_seconds=600,
        requires_audio=True,
        label="TikTok",
    ),
    Channel.YOUTUBE: VideoRequirement(
        aspect_ratios=frozenset({"9:16"}),
        min_duration_seconds=3,
        max_duration_seconds=60,
        requires_audio=False,
        label="YouTube Shorts",
    ),
}


def check_video_for_channel(metadata: VideoMetadata | None, channel: Channel) -> list[str]:
    """Trả danh sách lý do video KHÔNG đăng được lên kênh này. Rỗng = hợp lệ.

    `metadata is None` nghĩa là chưa đọc được thông số (ffprobe vắng mặt, hoặc
    file hỏng). Trả về một lý do rõ ràng chứ không phải danh sách rỗng: không
    biết mà báo hợp lệ là đúng kiểu sai đã khiến `FFmpegVideoProcessor` bản đầu
    dựng ra thông số 1920x1080 từ hư không.
    """
    requirement = VIDEO_REQUIREMENTS.get(channel)
    if requirement is None:
        return []
    if metadata is None:
        return ["Chưa đọc được thông số video nên chưa thể kiểm tra"]

    reasons: list[str] = []

    if requirement.aspect_ratios and metadata.aspect_ratio not in requirement.aspect_ratios:
        wanted = " hoặc ".join(sorted(requirement.aspect_ratios))
        reasons.append(
            f"{requirement.label} cần khung hình {wanted}, video này là {metadata.aspect_ratio}"
        )

    if metadata.duration_seconds < requirement.min_duration_seconds:
        reasons.append(
            f"{requirement.label} cần video dài ít nhất {requirement.min_duration_seconds:g} giây"
        )
    elif metadata.duration_seconds > requirement.max_duration_seconds:
        reasons.append(
            f"{requirement.label} chỉ nhận video tối đa "
            f"{requirement.max_duration_seconds:g} giây, video này "
            f"{metadata.duration_seconds:g} giây"
        )

    if requirement.requires_audio and not metadata.has_audio:
        reasons.append(f"{requirement.label} cần video có tiếng")

    return reasons


def eligible_channels(metadata: VideoMetadata | None) -> list[Channel]:
    """Kênh video mà clip này đăng được — dùng để UI gợi ý ngay sau khi upload."""
    return [
        channel for channel in VIDEO_REQUIREMENTS if not check_video_for_channel(metadata, channel)
    ]
