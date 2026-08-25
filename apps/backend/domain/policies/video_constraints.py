"""Video đăng được lên kênh nào — kiểm ngay lúc upload, không đợi tới lúc đăng.

Vì sao kiểm sớm: chủ tiệm quay clip bằng điện thoại rồi lên lịch đăng tối thứ
Bảy. Nếu ràng buộc chỉ được kiểm lúc scheduler gọi API nền tảng, thì cái sai
(quay ngang, dài quá, không có tiếng) chỉ lộ ra sau khi đã lỡ giờ đăng — và lúc
đó không sửa được nữa. Biết ngay lúc upload thì còn kịp quay lại.

**Khung hình so bằng số, không khớp nhãn.** Bản trước phân loại khung hình thành
vài ô rời rạc ("9:16", "1:1", "16:9", "4:5") rồi so khớp chuỗi tuyệt đối. Một
clip 720×1648 quay bằng điện thoại màn hình dài — tức là *dọc hơn* 9:16 — rơi ra
ngoài mọi ô, nhận nhãn thô `"720:1648"`, và bị **cả ba kênh** từ chối. Trong khi
chính clip đó upload thẳng từ điện thoại lên Reels, TikTok, Shorts đều được.

Sai theo hướng đó tệ hơn sai ngược lại: chặn nhầm thì chủ tiệm bỏ cuộc và nghĩ
app hỏng, mà không có dấu hiệu nào cho thấy lỗi nằm ở Havi. Nên luật ở đây là
**không bao giờ khắt khe hơn nền tảng** — nền tảng nhận cả một dải khung dọc rồi
tự cắt/thêm viền, Havi cũng phải nhận đúng dải đó.

Đây là domain policy thuần: không I/O, không SDK, chỉ số liệu vào và kết luận ra.
Con số lấy từ tài liệu công khai của từng nền tảng và sẽ lệch theo thời gian —
sửa ở đúng một chỗ này, và `VideoRequirement` mang theo lời giải thích để UI nói
được cho chủ tiệm bằng tiếng Việt thay vì hiện mã lỗi.
"""

from dataclasses import dataclass

from core.enums import Channel
from domain.ports.media import VideoMetadata

#: Dọc nhất mà Havi còn nhận, tính theo `rộng / cao`.
#:
#: 0.35 tương đương ~25:9 — dọc hơn mọi điện thoại đang bán (máy màn hình dài
#: nhất hiện nay quay ra ~20.6:9 = 0.437). Ngưỡng sàn tồn tại để chặn thứ thật
#: sự bất thường (một dải ảnh ghép dọc, một ảnh chụp màn hình chat kéo dài),
#: không phải để chặn điện thoại đời mới.
_MIN_VERTICAL_RATIO = 0.35

#: Ngang nhất mà kênh video dọc còn nhận: đúng hình vuông.
#:
#: Quá 1.0 là video nằm ngang. Nền tảng vẫn nhận rồi cắt hai bên, nhưng cắt một
#: video ngang thành khung dọc thì mất gần hết khung hình — chủ tiệm cần biết
#: điều đó *trước khi* đăng, chứ không phải sau.
_MAX_VERTICAL_RATIO = 1.0


@dataclass(frozen=True)
class VideoRequirement:
    """Ràng buộc video của một kênh. Khung hình tính theo `rộng / cao`."""

    #: Dải khung hình chấp nhận được, đã bao gồm hai đầu. `None` = kênh không kén.
    min_aspect_ratio: float | None
    max_aspect_ratio: float | None
    min_duration_seconds: float
    max_duration_seconds: float
    requires_audio: bool
    label: str
    #: Mô tả dải khung hình bằng lời, để thông báo lỗi đọc được. Con số trần trụi
    #: ("cần 0.35–1.0") không nói gì với người đang cầm điện thoại.
    shape_label: str = "khung dọc hoặc vuông"


#: Chỉ khai cho kênh video. Kênh ảnh/text không có mặt ở đây, và
#: `check_video_for_channel` coi kênh không khai là không ràng buộc.
VIDEO_REQUIREMENTS: dict[Channel, VideoRequirement] = {
    Channel.REELS: VideoRequirement(
        min_aspect_ratio=_MIN_VERTICAL_RATIO,
        max_aspect_ratio=_MAX_VERTICAL_RATIO,
        min_duration_seconds=3,
        max_duration_seconds=90,
        requires_audio=False,
        label="Facebook Reels",
    ),
    Channel.TIKTOK: VideoRequirement(
        min_aspect_ratio=_MIN_VERTICAL_RATIO,
        max_aspect_ratio=_MAX_VERTICAL_RATIO,
        min_duration_seconds=3,
        max_duration_seconds=600,
        requires_audio=True,
        label="TikTok",
    ),
    Channel.YOUTUBE: VideoRequirement(
        min_aspect_ratio=_MIN_VERTICAL_RATIO,
        # Shorts yêu cầu vuông hoặc dọc — đây là ràng buộc nền tảng công bố rõ,
        # không phải ước lượng như hai kênh trên.
        max_aspect_ratio=1.0,
        min_duration_seconds=3,
        max_duration_seconds=180,
        requires_audio=False,
        label="YouTube Shorts",
    ),
}


def aspect_ratio_of(metadata: VideoMetadata) -> float | None:
    """`rộng / cao`. `None` khi chưa đo được kích thước.

    Tính từ pixel thật chứ không đọc nhãn `aspect_ratio`: nhãn là chuỗi để hiển
    thị, và mọi lần so sánh dựa vào nó đều thừa hưởng đúng những cái ô rời rạc
    đã gây ra lỗi chặn nhầm.
    """
    if metadata.width <= 0 or metadata.height <= 0:
        return None
    return metadata.width / metadata.height


def describe_shape(metadata: VideoMetadata) -> str:
    """Khung hình nói bằng thứ chủ tiệm hình dung được, không phải số pixel.

    "khung 720:1648" không cho biết clip dọc hay ngang. "khung dọc 20.6:9" thì
    có — và khi bị từ chối, đó là khác biệt giữa "à, mình quay ngang" với "không
    hiểu app đang nói gì".
    """
    ratio = aspect_ratio_of(metadata)
    if ratio is None:
        return "chưa đọc được khung hình"
    if ratio < 1:
        return f"khung dọc {round(1 / ratio * 9, 1):g}:9"
    if ratio == 1:
        return "khung vuông 1:1"
    return f"khung ngang {round(ratio * 9, 1):g}:9"


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
    reasons.extend(_check_shape(metadata, requirement))

    if metadata.duration_seconds < requirement.min_duration_seconds:
        reasons.append(
            f"{requirement.label} cần video dài ít nhất "
            f"{requirement.min_duration_seconds:g} giây, video này "
            f"{metadata.duration_seconds:g} giây"
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


def _check_shape(metadata: VideoMetadata, requirement: VideoRequirement) -> list[str]:
    """Khung hình: so bằng số, và nói lý do bằng hình dạng chứ không bằng pixel."""
    if requirement.min_aspect_ratio is None and requirement.max_aspect_ratio is None:
        return []

    ratio = aspect_ratio_of(metadata)
    if ratio is None:
        return [f"{requirement.label}: chưa đọc được kích thước khung hình"]

    if requirement.max_aspect_ratio is not None and ratio > requirement.max_aspect_ratio:
        # Trường hợp hay gặp nhất: quay ngang rồi mang đi đăng kênh dọc.
        return [
            f"{requirement.label} cần {requirement.shape_label}, "
            f"video này là {describe_shape(metadata)}"
        ]

    if requirement.min_aspect_ratio is not None and ratio < requirement.min_aspect_ratio:
        return [
            f"{requirement.label} không nhận video dọc quá hẹp — "
            f"video này là {describe_shape(metadata)}"
        ]

    return []


def eligible_channels(metadata: VideoMetadata | None) -> list[Channel]:
    """Kênh video mà clip này đăng được — dùng để UI gợi ý ngay sau khi upload."""
    return [
        channel for channel in VIDEO_REQUIREMENTS if not check_video_for_channel(metadata, channel)
    ]
