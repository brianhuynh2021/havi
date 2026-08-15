"""Port cho Video Rendering Engine (Phase 3 Video Pipeline).

Domain port trừu tượng hoá việc render video (FFmpeg, Remotion, Cloud Worker).
Không phụ thuộc framework hay subprocess trực tiếp ở tầng domain.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


class VideoRenderError(Exception):
    """Lỗi xảy ra trong quá trình render video."""


class VideoRenderTimeout(VideoRenderError):
    """Quá thời gian render cho phép."""


class InvalidEditPlanError(VideoRenderError):
    """Cấu trúc EditPlan.json không hợp lệ."""


@dataclass(frozen=True)
class VideoRenderResult:
    """Kết quả đầu ra sau khi render video thành công."""

    output_file_path: str
    duration_seconds: float
    width: int
    height: int
    thumbnail_file_path: str | None = None


class VideoRendererPort(Protocol):
    """Hợp đồng cho bất kỳ video rendering engine nào (FFmpeg, Remotion)."""

    async def render(
        self,
        job_id: UUID,
        edit_plan: dict[str, Any],
        source_video_path: str,
        output_video_path: str,
        progress_callback: Callable[[int], Awaitable[None]] | None = None,
    ) -> VideoRenderResult:
        """Thực thi render video theo EditPlan và gọi progress_callback (0..100)."""
        ...
