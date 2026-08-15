"""Domain policy: Validation và cấu trúc EditPlan.json cho Video Editing Engine.

Xem docs/architecture/VIDEO_PIPELINE.md §4.
Policy thuần túy: không I/O, không gọi subprocess.
"""

from dataclasses import asdict, dataclass, field
from typing import Any

from core.enums import VideoCaptionStyle
from domain.ports.video_renderer import InvalidEditPlanError

VALID_ASPECT_RATIOS = frozenset({"9:16", "1:1", "16:9"})
MIN_DURATION_SECONDS = 2.0
MAX_DURATION_SECONDS = 600.0


@dataclass(frozen=True)
class VideoCut:
    start_ms: int
    end_ms: int
    zoom_scale: float = 1.0


@dataclass(frozen=True)
class VideoCaption:
    text: str
    start_ms: int
    end_ms: int
    style: VideoCaptionStyle = VideoCaptionStyle.BOLD_YELLOW


@dataclass(frozen=True)
class VideoAudioConfig:
    normalize_db: float = -14.0
    bg_music_volume: float = 0.15


@dataclass(frozen=True)
class EditPlan:
    target_aspect_ratio: str = "9:16"
    target_duration_seconds: float = 30.0
    cuts: list[VideoCut] = field(default_factory=list)
    captions: list[VideoCaption] = field(default_factory=list)
    audio: VideoAudioConfig = field(default_factory=VideoAudioConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_edit_plan(data: dict[str, Any] | None) -> EditPlan:
    """Validate dữ liệu JSON thành `EditPlan` chặt chẽ, ném `InvalidEditPlanError` nếu sai."""
    if not data or not isinstance(data, dict):
        raise InvalidEditPlanError("EditPlan phải là một JSON object")

    aspect_ratio = str(data.get("target_aspect_ratio", "9:16"))
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        valid_ratios = sorted(VALID_ASPECT_RATIOS)
        raise InvalidEditPlanError(
            f"Tỉ lệ khung hình '{aspect_ratio}' không hỗ trợ. Cho phép: {valid_ratios}"
        )

    try:
        duration = float(data.get("target_duration_seconds", 30.0))
    except (ValueError, TypeError) as exc:
        raise InvalidEditPlanError("target_duration_seconds phải là số thực") from exc

    if duration < MIN_DURATION_SECONDS or duration > MAX_DURATION_SECONDS:
        raise InvalidEditPlanError(
            f"Thời lượng video phải từ {MIN_DURATION_SECONDS}s đến {MAX_DURATION_SECONDS}s"
        )

    # Validate cuts
    cuts_data = data.get("cuts", [])
    if not isinstance(cuts_data, list):
        raise InvalidEditPlanError("Cuts phải là danh sách")

    validated_cuts: list[VideoCut] = []
    for idx, c in enumerate(cuts_data):
        if not isinstance(c, dict):
            raise InvalidEditPlanError(f"Cut #{idx} phải là object")
        start_ms = int(c.get("start_ms", 0))
        end_ms = int(c.get("end_ms", 0))
        if start_ms < 0 or end_ms <= start_ms:
            raise InvalidEditPlanError(
                f"Cut #{idx} có start_ms ({start_ms}) phải nhỏ hơn end_ms ({end_ms}) và >= 0"
            )
        zoom = float(c.get("zoom_scale", 1.0))
        if zoom < 0.5 or zoom > 2.0:
            raise InvalidEditPlanError(f"Cut #{idx} có zoom_scale ({zoom}) ngoài khoảng [0.5, 2.0]")
        validated_cuts.append(VideoCut(start_ms=start_ms, end_ms=end_ms, zoom_scale=zoom))

    # Validate captions
    captions_data = data.get("captions", [])
    if not isinstance(captions_data, list):
        raise InvalidEditPlanError("Captions phải là danh sách")

    validated_captions: list[VideoCaption] = []
    for idx, cap in enumerate(captions_data):
        if not isinstance(cap, dict):
            raise InvalidEditPlanError(f"Caption #{idx} phải là object")
        text = str(cap.get("text", "")).strip()
        if not text:
            raise InvalidEditPlanError(f"Caption #{idx} không được để trống text")
        if len(text) > 150:
            raise InvalidEditPlanError(f"Caption #{idx} vượt quá 150 ký tự: '{text[:30]}...'")

        start_ms = int(cap.get("start_ms", 0))
        end_ms = int(cap.get("end_ms", 0))
        if start_ms < 0 or end_ms <= start_ms:
            raise InvalidEditPlanError(
                f"Caption #{idx} có timecode ({start_ms}-{end_ms}ms) không hợp lệ"
            )

        style_raw = cap.get("style", VideoCaptionStyle.BOLD_YELLOW.value)
        try:
            style = VideoCaptionStyle(style_raw)
        except ValueError:
            style = VideoCaptionStyle.BOLD_YELLOW

        validated_captions.append(
            VideoCaption(text=text, start_ms=start_ms, end_ms=end_ms, style=style)
        )

    # Audio config
    audio_data = data.get("audio", {})
    if not isinstance(audio_data, dict):
        audio_data = {}

    norm_db = float(audio_data.get("normalize_db", -14.0))
    bgm_vol = float(audio_data.get("bg_music_volume", 0.15))
    if bgm_vol < 0.0 or bgm_vol > 1.0:
        raise InvalidEditPlanError("bg_music_volume phải từ 0.0 đến 1.0")

    audio_cfg = VideoAudioConfig(normalize_db=norm_db, bg_music_volume=bgm_vol)

    return EditPlan(
        target_aspect_ratio=aspect_ratio,
        target_duration_seconds=duration,
        cuts=validated_cuts,
        captions=validated_captions,
        audio=audio_cfg,
    )


def default_edit_plan_for_short_form(
    duration_seconds: float, hook_text: str = ""
) -> dict[str, Any]:
    """Tạo EditPlan mặc định chuẩn 9:16 với Hook 3 giây đầu cho TikTok / Reels / Shorts."""
    dur_ms = int(duration_seconds * 1000)
    hook_end_ms = min(3500, dur_ms)
    captions = []
    if hook_text.strip():
        captions.append(
            {
                "text": hook_text.strip(),
                "start_ms": 0,
                "end_ms": hook_end_ms,
                "style": VideoCaptionStyle.BOLD_YELLOW.value,
            }
        )

    return {
        "target_aspect_ratio": "9:16",
        "target_duration_seconds": round(duration_seconds, 1),
        "cuts": [{"start_ms": 0, "end_ms": dur_ms, "zoom_scale": 1.0}],
        "captions": captions,
        "audio": {"normalize_db": -14.0, "bg_music_volume": 0.15},
    }
