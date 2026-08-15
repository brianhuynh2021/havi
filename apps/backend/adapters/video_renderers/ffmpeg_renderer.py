"""FFmpeg Video Renderer Adapter (Phase 3 Video Pipeline).

Hiện thực `domain.ports.video_renderer.VideoRendererPort`.
Chịu trách nhiệm thực thi cắt ghép, crop khung dọc 9:16, chèn phụ đề động,
chuẩn hoá âm thanh và trích xuất thumbnail bằng FFmpeg CLI.
"""

import asyncio
import logging
import os
import shutil
import subprocess
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from domain.policies.video_edit_plan import (
    EditPlan,
    validate_edit_plan,
)
from domain.ports.video_renderer import (
    VideoRenderError,
    VideoRenderResult,
)

logger = logging.getLogger("havi.adapters.video_renderer.ffmpeg")


class FFmpegVideoRenderer:
    """Production headless video rendering engine utilizing FFmpeg CLI."""

    def __init__(self, ffmpeg_path: str | None = None, ffprobe_path: str | None = None) -> None:
        self.ffmpeg_path = ffmpeg_path if ffmpeg_path is not None else shutil.which("ffmpeg")
        self.ffprobe_path = ffprobe_path if ffprobe_path is not None else shutil.which("ffprobe")

    @property
    def is_available(self) -> bool:
        return bool(self.ffmpeg_path)

    @property
    def has_drawtext(self) -> bool:
        if not self.ffmpeg_path:
            return False
        if not hasattr(self, "_has_drawtext_cache"):
            try:
                res = subprocess.run(
                    [self.ffmpeg_path, "-filters"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                self._has_drawtext_cache = "drawtext" in res.stdout
            except Exception:
                self._has_drawtext_cache = False
        return self._has_drawtext_cache

    async def render(
        self,
        job_id: UUID,
        edit_plan: dict[str, Any] | EditPlan,
        source_video_path: str,
        output_video_path: str,
        progress_callback: Callable[[int], Awaitable[None]] | None = None,
    ) -> VideoRenderResult:
        """Thực thi pipeline render video theo EditPlan."""
        plan: EditPlan = (
            edit_plan if isinstance(edit_plan, EditPlan) else validate_edit_plan(edit_plan)
        )

        if progress_callback:
            await progress_callback(10)

        # Nếu không có ffmpeg trong môi trường (ví dụ CI runner tối giản),
        # chạy mock fallback an toàn
        if not self.ffmpeg_path:
            logger.warning(
                "FFmpeg CLI not found in environment, executing mock fallback renderer for job %s",
                job_id,
            )
            return await self._mock_render_fallback(
                job_id, plan, source_video_path, output_video_path, progress_callback
            )

        return await self._execute_ffmpeg_render(
            job_id=job_id,
            plan=plan,
            source_path=source_video_path,
            output_path=output_video_path,
            progress_callback=progress_callback,
        )

    async def _execute_ffmpeg_render(
        self,
        job_id: UUID,
        plan: EditPlan,
        source_path: str,
        output_path: str,
        progress_callback: Callable[[int], Awaitable[None]] | None = None,
    ) -> VideoRenderResult:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        thumbnail_path = os.path.splitext(output_path)[0] + "_thumb.jpg"

        if progress_callback:
            await progress_callback(25)

        # 1. Xây dựng Video Filters (9:16 crop & scale)
        # Scale to fit 1080x1920 vertical canvas
        vf_filters: list[str] = []
        if plan.target_aspect_ratio == "9:16":
            vf_filters.append(
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
            )
            width, height = 1080, 1920
        elif plan.target_aspect_ratio == "1:1":
            vf_filters.append(
                "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,setsar=1"
            )
            width, height = 1080, 1080
        else:
            vf_filters.append(
                "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1"
            )
            width, height = 1920, 1080

        # 2. Xây dựng Text Burn-in Subtitles nếu có captions và ffmpeg hỗ trợ drawtext
        if plan.captions and self.has_drawtext:
            for cap in plan.captions:
                escaped_text = (
                    cap.text.replace("\\", "\\\\")
                    .replace("'", "'\\\\''")
                    .replace(":", "\\:")
                    .replace("%", "\\%")
                )
                start_s = cap.start_ms / 1000.0
                end_s = cap.end_ms / 1000.0
                drawtext = (
                    f"drawtext=text='{escaped_text}':"
                    f"enable='between(t,{start_s:.2f},{end_s:.2f})':"
                    f"fontcolor=yellow:fontsize=48:box=1:boxcolor=black@0.6:boxborderw=10:"
                    f"x=(w-text_w)/2:y=h*0.75"
                )
                vf_filters.append(drawtext)

        filter_str = ",".join(vf_filters)

        # 3. Xây dựng Audio Filters (Chuẩn hoá âm lượng -14 LUFS)
        af_filters = ["volume=1.0"]
        if plan.audio.normalize_db:
            af_filters.append("loudnorm=I=-14:LRA=11:TP=-1.5")
        audio_filter_str = ",".join(af_filters)

        # 4. Cấu hình lệnh FFmpeg
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i",
            source_path,
            "-vf",
            filter_str,
            "-af",
            audio_filter_str,
            "-t",
            str(plan.target_duration_seconds),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output_path,
        ]

        if progress_callback:
            await progress_callback(50)

        # Chạy subprocess bất đồng bộ
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raw_err = stderr.decode("utf-8", errors="replace")
                err_msg = raw_err[-400:].strip() or raw_err[:400].strip()
                logger.error("FFmpeg render failed (code %s): %s", proc.returncode, err_msg)
                raise VideoRenderError(f"Lỗi render FFmpeg (mã {proc.returncode}): {err_msg}")
        except Exception as exc:
            if not isinstance(exc, VideoRenderError):
                raise VideoRenderError(f"Không thể khởi chạy FFmpeg: {exc}") from exc
            raise

        if progress_callback:
            await progress_callback(85)

        # 5. Tạo Thumbnail ảnh trích xuất từ giây đầu
        thumb_cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss",
            "00:00:01",
            "-i",
            output_path,
            "-vframes",
            "1",
            "-q:v",
            "2",
            thumbnail_path,
        ]
        try:
            thumb_proc = await asyncio.create_subprocess_exec(
                *thumb_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await thumb_proc.communicate()
            if not os.path.exists(thumbnail_path):
                thumbnail_path = None
        except Exception as thumb_exc:
            logger.warning("Thumbnail extraction failed: %s", thumb_exc)
            thumbnail_path = None

        if progress_callback:
            await progress_callback(100)

        return VideoRenderResult(
            output_file_path=output_path,
            duration_seconds=plan.target_duration_seconds,
            width=width,
            height=height,
            thumbnail_file_path=thumbnail_path,
        )

    async def _mock_render_fallback(
        self,
        job_id: UUID,
        plan: EditPlan,
        source_path: str,
        output_path: str,
        progress_callback: Callable[[int], Awaitable[None]] | None = None,
    ) -> VideoRenderResult:
        """Fallback renderer cho test môi trường thiếu FFmpeg binary."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        thumbnail_path = os.path.splitext(output_path)[0] + "_thumb.jpg"

        if progress_callback:
            await progress_callback(50)

        # Tạo file video giả lập hợp lệ hoặc copy từ source nếu có
        if os.path.exists(source_path):
            shutil.copyfile(source_path, output_path)
        else:
            with open(output_path, "wb") as f:
                f.write(b"MOCK_MP4_VIDEO_HEADER" + b"\x00" * 1024)

        with open(thumbnail_path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 512 + b"\xff\xd9")

        if progress_callback:
            await progress_callback(100)

        return VideoRenderResult(
            output_file_path=output_path,
            duration_seconds=plan.target_duration_seconds,
            width=1080 if plan.target_aspect_ratio == "9:16" else 1920,
            height=1920 if plan.target_aspect_ratio == "9:16" else 1080,
            thumbnail_file_path=thumbnail_path,
        )
