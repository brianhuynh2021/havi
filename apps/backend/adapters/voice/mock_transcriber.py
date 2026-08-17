"""Mock Voice Transcriber — cho kiểm thử và môi trường local."""

from domain.ports.voice_transcriber import (
    TranscribeResult,
    VoiceTranscribeError,
    VoiceTranscriberPort,
)


class MockVoiceTranscriber(VoiceTranscriberPort):
    """Mock chuyển giọng nói cho unit/integration test mà không cần gọi API mạng."""

    def __init__(self, default_text: str | None = None) -> None:
        self._default_text = default_text or (
            "Hôm nay tiệm em giảm 30% gói gội đầu dưỡng sinh thảo dược và uốn nhuộm phục hồi nhân dịp khai trương, "
            "tặng kèm hấp dầu collagen cho 20 khách đầu tiên đặt lịch sớm."
        )

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str,
        *,
        language: str = "vi",
    ) -> TranscribeResult:
        if not audio_bytes:
            raise VoiceTranscribeError("File âm thanh rỗng.")

        return TranscribeResult(
            text=self._default_text,
            summary="Ưu đãi giảm giá 30% khai trương",
            detected_intent="khuyen_mai",
        )
