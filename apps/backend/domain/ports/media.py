"""Port cho việc đọc metadata của video.

`VideoMetadata` sống ở domain chứ không ở adapter: nó là hợp đồng giữa
`MediaService` và bất kỳ cách probe nào (ffprobe CLI hôm nay, một service khác
sau này), và `domain/policies/video_constraints.py` đọc nó để quyết định video có
đăng được lên kênh nào.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class VideoMetadata:
    duration_seconds: float
    width: int
    height: int
    #: "9:16" | "16:9" | "1:1" | "4:5" | "unknown" | "<w>:<h>" khi không rơi vào
    #: khung nào quen thuộc.
    aspect_ratio: str
    has_audio: bool


class VideoProcessorPort(Protocol):
    """Đọc thông số kỹ thuật của một video.

    Trả `None` khi không đọc được — KHÔNG trả số mặc định. Đây là điểm quan trọng:
    bản đầu của `FFmpegVideoProcessor` trả 1920x1080/16:9 khi ffprobe vắng mặt
    hoặc bytes hỏng, nghĩa là một file hỏng sẽ được ghi vào DB như một video
    Full HD hợp lệ, rồi lọt qua kiểm tra ràng buộc kênh và chỉ vỡ ra ở lúc đăng.
    Không biết thì phải nói là không biết.
    """

    @property
    def is_available(self) -> bool: ...

    def probe_bytes(
        self, video_bytes: bytes, filename_hint: str = "temp.mp4"
    ) -> VideoMetadata | None: ...

    def thumbnail_bytes(
        self,
        video_bytes: bytes,
        filename_hint: str = "temp.mp4",
        timestamp_seconds: float = 1.0,
    ) -> bytes | None:
        """JPEG một khung hình, hoặc `None` khi không lấy được.

        Cùng quy tắc như `probe_bytes`: không đọc được thì nói là không đọc được.
        Ảnh bìa không lấy được là chuyện nhỏ (UI hiện placeholder), nhưng trả về
        một khung hình đen dựng sẵn thì chủ tiệm tưởng clip mình quay bị đen.
        """
        ...
