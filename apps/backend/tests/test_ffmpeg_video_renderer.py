"""Unit test suite cho `FFmpegVideoRenderer` adapter."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from adapters.video_renderers.ffmpeg_renderer import FFmpegVideoRenderer
from domain.policies.video_edit_plan import default_edit_plan_for_short_form

requires_ffmpeg = pytest.mark.skipif(
    not shutil.which("ffmpeg"),
    reason="cần ffmpeg trong PATH",
)


def _make_test_video(
    path: Path, *, width: int = 540, height: int = 960, seconds: float = 3.0
) -> Path:
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=size={width}x{height}:rate=30:duration={seconds}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={seconds}",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


@pytest.mark.asyncio
async def test_ffmpeg_renderer_fallback_creates_valid_output():
    # Buộc chạy mock fallback bằng cách truyền rỗng cho binary path
    renderer = FFmpegVideoRenderer(ffmpeg_path="")
    job_id = uuid4()
    plan = default_edit_plan_for_short_form(5.0, hook_text="Hook Giữ Chân 3 Giây")

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = os.path.join(tmp_dir, "input.mp4")
        output_path = os.path.join(tmp_dir, "output.mp4")
        with open(source_path, "wb") as f:
            f.write(b"RAW_VIDEO_BYTES_TEST")

        progress_updates = []

        async def track_progress(pct: int) -> None:
            progress_updates.append(pct)

        result = await renderer.render(
            job_id=job_id,
            edit_plan=plan,
            source_video_path=source_path,
            output_video_path=output_path,
            progress_callback=track_progress,
        )

        assert os.path.exists(result.output_file_path)
        assert result.width == 1080
        assert result.height == 1920
        assert result.duration_seconds == 5.0
        assert 100 in progress_updates


@requires_ffmpeg
@pytest.mark.asyncio
async def test_ffmpeg_renderer_real_transcode_and_crop():
    renderer = FFmpegVideoRenderer()
    job_id = uuid4()
    plan = default_edit_plan_for_short_form(2.0, hook_text="Tiệm Spa Havi 3s Hook")

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = Path(tmp_dir) / "source_clip.mp4"
        output_path = Path(tmp_dir) / "output_reel.mp4"
        _make_test_video(source_path, width=640, height=480, seconds=2.0)

        result = await renderer.render(
            job_id=job_id,
            edit_plan=plan,
            source_video_path=str(source_path),
            output_video_path=str(output_path),
        )

        assert os.path.exists(result.output_file_path)
        assert result.width == 1080
        assert result.height == 1920
        assert result.duration_seconds == 2.0
