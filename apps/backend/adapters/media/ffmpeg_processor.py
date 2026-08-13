"""Adapter đọc thông số video bằng ffprobe/ffmpeg CLI.

Hiện thực `domain.ports.media.VideoProcessorPort`. Không đọc được thì trả `None`
— lý do nằm ở docstring của port.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile

from domain.ports.media import VideoMetadata

logger = logging.getLogger("havi.adapters.media.ffmpeg")

__all__ = ["FFmpegVideoProcessor", "VideoMetadata"]


class FFmpegVideoProcessor:
    """FFmpeg-based video probing and frame extraction service."""

    def __init__(self) -> None:
        self.ffprobe_path = shutil.which("ffprobe")
        self.ffmpeg_path = shutil.which("ffmpeg")

    @property
    def is_available(self) -> bool:
        return bool(self.ffprobe_path and self.ffmpeg_path)

    def probe_file(self, file_path: str) -> VideoMetadata | None:
        """Đọc thông số video bằng ffprobe. `None` khi không đọc được.

        Không dựng số mặc định: bản đầu trả 1920x1080/16:9 khi ffprobe vắng mặt,
        nên một file hỏng được ghi vào DB như video Full HD hợp lệ và chỉ vỡ ra ở
        lúc đăng. Xem `domain/ports/media.VideoProcessorPort`.
        """
        if not self.ffprobe_path:
            logger.warning("ffprobe CLI is not available in environment; skipping probe")
            return None

        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)

            streams = data.get("streams", [])
            format_info = data.get("format", {})

            video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

            duration = float(format_info.get("duration") or video_stream.get("duration") or 0.0)
            width = int(video_stream.get("width") or 0)
            height = int(video_stream.get("height") or 0)

            aspect_ratio = self.classify_aspect_ratio(width, height)

            return VideoMetadata(
                duration_seconds=round(duration, 2),
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                has_audio=audio_stream is not None,
            )
        except Exception as exc:
            logger.error("Failed to probe video file with ffprobe: %s", exc)
            return None

    def probe_bytes(
        self, video_bytes: bytes, filename_hint: str = "temp.mp4"
    ) -> VideoMetadata | None:
        """Probe video metadata from raw byte buffer."""
        suffix = os.path.splitext(filename_hint)[1] or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        try:
            return self.probe_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def extract_thumbnail(
        self, file_path: str, timestamp_seconds: float = 1.0
    ) -> bytes | None:
        """Extract a single JPEG frame thumbnail from the video using ffmpeg."""
        if not self.ffmpeg_path:
            logger.warning("ffmpeg CLI is not available in environment; thumbnail skipped")
            return None

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_out:
            out_path = tmp_out.name

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(timestamp_seconds),
            "-i", file_path,
            "-vframes", "1",
            "-q:v", "2",
            out_path,
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                with open(out_path, "rb") as f:
                    return f.read()
            return None
        except Exception as exc:
            logger.error("Failed to extract video thumbnail with ffmpeg: %s", exc)
            return None
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    @staticmethod
    def classify_aspect_ratio(width: int, height: int) -> str:
        if width <= 0 or height <= 0:
            return "unknown"
        ratio = width / height
        if 0.5 <= ratio <= 0.65:  # ~9:16 (0.5625)
            return "9:16"
        if 1.7 <= ratio <= 1.85:  # ~16:9 (1.7777)
            return "16:9"
        if 0.9 <= ratio <= 1.1:   # ~1:1 (1.0)
            return "1:1"
        if 0.75 <= ratio <= 0.85: # ~4:5 (0.8)
            return "4:5"
        return f"{width}:{height}"
