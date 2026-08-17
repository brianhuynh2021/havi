"""Voice Service — xử lý tiếp nhận file ghi âm và điều phối chuyển giọng nói thành bài đăng."""

import logging
from typing import Any
from uuid import UUID

from adapters.persistence.event_log_repository import EventLogRepository
from core.events import EventLogEntry
from domain.models.content import ContentJob
from domain.ports.voice_transcriber import (
    TranscribeResult,
    VoiceTranscribeError,
    VoiceTranscriberPort,
)

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_MIMES = {
    "audio/webm",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/m4a",
    "audio/x-m4a",
    "audio/aac",
    "audio/flac",
    "video/webm",  # browser MediaRecorder sometimes outputs video/webm container with audio only
}

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB


class InvalidAudioFormatError(Exception):
    """Định dạng audio không được hỗ trợ."""

    def __init__(self, mime_type: str) -> None:
        super().__init__(f"Định dạng âm thanh '{mime_type}' không được hỗ trợ.")
        self.mime_type = mime_type


class AudioPayloadTooLargeError(Exception):
    """File âm thanh vượt quá giới hạn dung lượng."""

    def __init__(self, size_bytes: int) -> None:
        super().__init__(f"File âm thanh vượt quá giới hạn 25MB (kích thước: {size_bytes} bytes).")
        self.size_bytes = size_bytes


class VoiceService:
    """Điều phối nhận diện giọng nói và tự động chuyển đổi thành bài đăng tiếp thị."""

    def __init__(
        self,
        transcriber: VoiceTranscriberPort,
        events: EventLogRepository,
    ) -> None:
        self._transcriber = transcriber
        self._events = events

    def _validate_audio(self, audio_bytes: bytes, mime_type: str) -> None:
        clean_mime = mime_type.split(";")[0].strip().lower()
        if clean_mime not in SUPPORTED_AUDIO_MIMES:
            raise InvalidAudioFormatError(mime_type)

        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise AudioPayloadTooLargeError(len(audio_bytes))

        if len(audio_bytes) == 0:
            raise VoiceTranscribeError("File âm thanh rỗng.")

    async def transcribe_voice(
        self,
        *,
        workspace_id: UUID,
        audio_bytes: bytes,
        mime_type: str,
    ) -> TranscribeResult:
        """Nhận diện giọng nói tiếng Việt và trả về văn bản sạch."""
        self._validate_audio(audio_bytes, mime_type)

        clean_mime = mime_type.split(";")[0].strip().lower()
        result = await self._transcriber.transcribe(audio_bytes, clean_mime)

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="voice.transcribed",
                input_summary=f"Audio {clean_mime} ({len(audio_bytes)} bytes)",
                output_summary=f"STT: {result.text[:200]}",
            )
        )

        return result

    async def voice_to_content(
        self,
        *,
        workspace_id: UUID,
        audio_bytes: bytes,
        mime_type: str,
        content_service: Any,
        idempotency_key: str | None = None,
    ) -> tuple[TranscribeResult, ContentJob]:
        """Quy trình 1-chạm: Ghi âm -> Nhận diện giọng nói -> Tự động tạo Job sinh bài đa kênh."""
        transcribe_result = await self.transcribe_voice(
            workspace_id=workspace_id,
            audio_bytes=audio_bytes,
            mime_type=mime_type,
        )

        raw_inputs = [
            {
                "kind": "text",
                "text": transcribe_result.text,
                "media_note": f"Ghi âm giọng nói chủ tiệm: {transcribe_result.summary}",
            }
        ]

        created_job = await content_service.create_job(
            workspace_id=workspace_id,
            raw_inputs=raw_inputs,
            idempotency_key=idempotency_key,
        )

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="voice.voice_to_content_created",
                input_summary=f"Ghi âm giọng nói ({transcribe_result.summary})",
                output_summary=f"Tạo Content Job {created_job.job.id} thành công",
            )
        )

        return transcribe_result, created_job.job
