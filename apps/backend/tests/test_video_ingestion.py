"""Ingestion video: probe thật bằng ffmpeg + ràng buộc kênh.

Test dựng video thật bằng ffmpeg rồi probe lại, thay vì mock ffprobe. Lý do: cái
dễ sai ở đây không phải luồng gọi hàm mà là *diễn giải output của ffprobe* —
duration nằm ở `format` hay ở `stream`, stream nào là video khi file có nhiều
stream, tỉ lệ nào thì tính là 9:16. Mock sẽ khoá lại đúng những giả định sai đó.

Bỏ qua khi máy không có ffmpeg thay vì để đỏ, để một máy dev thiếu binary không
bị chặn. CI *có* cài ffmpeg (`.github/workflows/ci.yml`), nên các test này chạy
thật ở đó — skip không còn là chỗ để lỗi trốn.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from adapters.media.ffmpeg_processor import FFmpegVideoProcessor
from core.enums import Channel
from domain.policies.video_constraints import (
    check_video_for_channel,
    eligible_channels,
)
from domain.ports.media import VideoMetadata

ffmpeg_required = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
    reason="cần ffmpeg/ffprobe trong PATH",
)


def _make_video(
    path: Path, *, width: int, height: int, seconds: float, audio: bool
) -> Path:
    """Dựng một clip thật bằng ffmpeg testsrc."""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"testsrc=size={width}x{height}:rate=30:duration={seconds}",
    ]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-shortest"]
    cmd += ["-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


@pytest.fixture
def processor() -> FFmpegVideoProcessor:
    return FFmpegVideoProcessor()


class TestAspectRatioClassification:
    def test_known_ratios(self, processor: FFmpegVideoProcessor):
        assert processor.classify_aspect_ratio(1080, 1920) == "9:16"
        assert processor.classify_aspect_ratio(1920, 1080) == "16:9"
        assert processor.classify_aspect_ratio(1080, 1080) == "1:1"
        assert processor.classify_aspect_ratio(1080, 1350) == "4:5"

    def test_zero_dimensions_are_unknown_not_a_guess(
        self, processor: FFmpegVideoProcessor
    ):
        assert processor.classify_aspect_ratio(0, 0) == "unknown"
        assert processor.classify_aspect_ratio(1920, 0) == "unknown"


class TestProbeHonesty:
    def test_garbage_bytes_return_none_not_fabricated_metadata(
        self, processor: FFmpegVideoProcessor
    ):
        """Bytes hỏng phải ra `None`.

        Bản đầu trả 1920x1080/16:9 cho mọi thất bại, nghĩa là một file hỏng được
        ghi vào DB như video Full HD hợp lệ, lọt qua kiểm ràng buộc kênh, và chỉ
        vỡ ra lúc đăng.
        """
        assert processor.probe_bytes(b"khong-phai-video") is None

    def test_missing_file_returns_none(self, processor: FFmpegVideoProcessor):
        assert processor.probe_file("/khong/ton/tai/clip.mp4") is None


@ffmpeg_required
class TestProbeRealVideo:
    def test_vertical_clip_with_audio(self, processor: FFmpegVideoProcessor):
        with tempfile.TemporaryDirectory() as tmp:
            path = _make_video(
                Path(tmp) / "vertical.mp4", width=540, height=960, seconds=4, audio=True
            )
            meta = processor.probe_file(str(path))

        assert meta is not None
        assert meta.width == 540
        assert meta.height == 960
        assert meta.aspect_ratio == "9:16"
        assert meta.has_audio is True
        assert 3.5 <= meta.duration_seconds <= 4.5

    def test_landscape_clip_without_audio(self, processor: FFmpegVideoProcessor):
        with tempfile.TemporaryDirectory() as tmp:
            path = _make_video(
                Path(tmp) / "wide.mp4", width=1280, height=720, seconds=4, audio=False
            )
            meta = processor.probe_file(str(path))

        assert meta is not None
        assert meta.aspect_ratio == "16:9"
        assert meta.has_audio is False

    def test_probe_bytes_matches_probe_file(self, processor: FFmpegVideoProcessor):
        with tempfile.TemporaryDirectory() as tmp:
            path = _make_video(
                Path(tmp) / "clip.mp4", width=540, height=960, seconds=3, audio=True
            )
            from_file = processor.probe_file(str(path))
            from_bytes = processor.probe_bytes(path.read_bytes(), "clip.mp4")

        assert from_file == from_bytes

    def test_thumbnail_extracted_from_real_video(self, processor: FFmpegVideoProcessor):
        with tempfile.TemporaryDirectory() as tmp:
            path = _make_video(
                Path(tmp) / "clip.mp4", width=540, height=960, seconds=4, audio=False
            )
            thumb = processor.extract_thumbnail(str(path), timestamp_seconds=1.0)

        assert thumb is not None
        assert thumb.startswith(b"\xff\xd8"), "phải là JPEG"

    def test_thumbnail_bytes_works_from_buffer(self, processor: FFmpegVideoProcessor):
        """`MediaService` chỉ có bytes trong tay, không có đường dẫn file."""
        with tempfile.TemporaryDirectory() as tmp:
            path = _make_video(
                Path(tmp) / "clip.mp4", width=540, height=960, seconds=4, audio=False
            )
            thumb = processor.thumbnail_bytes(path.read_bytes(), "clip.mp4")

        assert thumb is not None
        assert thumb.startswith(b"\xff\xd8"), "phải là JPEG"

    def test_thumbnail_falls_back_when_seek_passes_end_of_clip(
        self, processor: FFmpegVideoProcessor
    ):
        """Clip ngắn hơn mốc seek vẫn phải có bìa.

        `-ss 1.0` trên clip 0.5 giây nhảy quá đuôi video và ffmpeg không xuất
        khung nào — chủ tiệm quay một cái vèo rồi upload là chuyện thường, và ô
        trống trong thư viện trông như upload lỗi.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = _make_video(
                Path(tmp) / "short.mp4", width=540, height=960, seconds=0.5, audio=False
            )
            thumb = processor.thumbnail_bytes(
                path.read_bytes(), "short.mp4", timestamp_seconds=1.0
            )

        assert thumb is not None
        assert thumb.startswith(b"\xff\xd8"), "phải là JPEG"

    def test_thumbnail_bytes_returns_none_for_garbage(
        self, processor: FFmpegVideoProcessor
    ):
        assert processor.thumbnail_bytes(b"khong-phai-video") is None


def _meta(
    *, ratio: str = "9:16", seconds: float = 20, audio: bool = True
) -> VideoMetadata:
    return VideoMetadata(
        duration_seconds=seconds,
        width=1080,
        height=1920,
        aspect_ratio=ratio,
        has_audio=audio,
    )


class TestChannelConstraints:
    def test_vertical_clip_passes_every_video_channel(self):
        assert set(eligible_channels(_meta(seconds=30))) == {
            Channel.REELS,
            Channel.TIKTOK,
            Channel.YOUTUBE,
        }

    def test_landscape_clip_rejected_by_short_form_channels(self):
        wide = _meta(ratio="16:9")
        assert eligible_channels(wide) == []
        reasons = check_video_for_channel(wide, Channel.REELS)
        assert any("khung hình" in reason for reason in reasons)

    def test_youtube_shorts_rejects_over_sixty_seconds(self):
        long_clip = _meta(seconds=75)
        assert Channel.YOUTUBE not in eligible_channels(long_clip)
        # Reels cho tới 90 giây nên vẫn nhận.
        assert Channel.REELS in eligible_channels(long_clip)

    def test_tiktok_requires_audio(self):
        silent = _meta(audio=False)
        reasons = check_video_for_channel(silent, Channel.TIKTOK)
        assert any("tiếng" in reason for reason in reasons)
        # Reels không bắt buộc có tiếng.
        assert check_video_for_channel(silent, Channel.REELS) == []

    def test_too_short_clip_rejected(self):
        assert eligible_channels(_meta(seconds=1)) == []

    def test_unprobed_video_is_refused_not_assumed_valid(self):
        """`None` phải ra lý do rõ ràng, không phải danh sách rỗng.

        Danh sách rỗng nghĩa là "hợp lệ" — trả vậy cho một video chưa đọc được
        thông số là đúng kiểu đoán bừa mà cả module này tồn tại để tránh.
        """
        reasons = check_video_for_channel(None, Channel.TIKTOK)
        assert reasons and "chưa" in reasons[0].lower()
        assert eligible_channels(None) == []

    def test_non_video_channels_have_no_video_constraints(self):
        assert check_video_for_channel(_meta(ratio="16:9"), Channel.FACEBOOK_PAGE) == []
        assert check_video_for_channel(None, Channel.ZALO_OA) == []
