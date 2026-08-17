"""Voice transcriber port — chuyển âm thanh ghi âm giọng nói thành văn bản."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class VoiceTranscribeError(Exception):
    """Lỗi chuyển đổi giọng nói thành văn bản."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class TranscribeResult:
    """Kết quả nhận diện giọng nói tiếng Việt."""

    text: str
    summary: str = ""
    detected_intent: str = ""


class VoiceTranscriberPort(ABC):
    """Port chuyển giọng nói thành văn bản cho Havi."""

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str,
        *,
        language: str = "vi",
    ) -> TranscribeResult:
        """Chuyển đổi file âm thanh thành văn bản tiếng Việt."""
        raise NotImplementedError
