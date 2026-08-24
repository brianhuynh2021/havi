"""Router /voice — nhận diện giọng nói và tự động tạo bài đăng tiếp thị từ âm thanh ghi âm."""

import base64
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from api.deps import ActiveWorkspaceDep, ContentServiceDep, VoiceServiceDep, WorkspaceDep
from application.services.voice_service import (
    AudioPayloadTooLargeError,
    InvalidAudioFormatError,
)
from domain.ports.voice_transcriber import VoiceTranscribeError

router = APIRouter(prefix="/voice", tags=["voice"])


class Base64VoiceRequest(BaseModel):
    """Payload nhận diện âm thanh dạng base64 từ trình duyệt / mobile app."""

    audio_base64: str = Field(..., description="Chuỗi base64 của file âm thanh")
    mime_type: str = Field(
        default="audio/webm", description="MIME type của âm thanh (audio/webm, audio/mp4...)"
    )


class VoiceTranscribeResponse(BaseModel):
    """Kết quả nhận diện giọng nói."""

    text: str
    summary: str
    detected_intent: str


class VoiceToContentResponse(BaseModel):
    """Kết quả quy trình 1-chạm tạo bài từ giọng nói."""

    text: str
    summary: str
    detected_intent: str
    job_id: UUID
    job_status: str


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_voice_note(
    payload: Base64VoiceRequest,
    workspace_id: ActiveWorkspaceDep,
    voice_service: VoiceServiceDep,
) -> VoiceTranscribeResponse:
    """Chuyển đổi file ghi âm giọng nói thành văn bản tiếng Việt chuẩn xác."""
    if not payload.audio_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng cung cấp chuỗi audio_base64",
        )

    try:
        audio_bytes = base64.b64decode(payload.audio_base64)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dữ liệu audio_base64 không hợp lệ",
        ) from exc

    try:
        res = await voice_service.transcribe_voice(
            workspace_id=workspace_id,
            audio_bytes=audio_bytes,
            mime_type=payload.mime_type,
        )
        return VoiceTranscribeResponse(
            text=res.text,
            summary=res.summary,
            detected_intent=res.detected_intent,
        )
    except InvalidAudioFormatError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except AudioPayloadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except VoiceTranscribeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/voice-to-content", response_model=VoiceToContentResponse)
async def voice_to_content(
    payload: Base64VoiceRequest,
    workspace_id: ActiveWorkspaceDep,
    voice_service: VoiceServiceDep,
    content_service: ContentServiceDep,
) -> VoiceToContentResponse:
    """1-Chạm: Ghi âm giọng nói -> Chuyển thành văn bản -> Tự động tạo Job sinh bài đa kênh."""
    if not payload.audio_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng cung cấp chuỗi audio_base64",
        )

    try:
        audio_bytes = base64.b64decode(payload.audio_base64)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dữ liệu audio_base64 không hợp lệ",
        ) from exc

    try:
        transcribe_res, job = await voice_service.voice_to_content(
            workspace_id=workspace_id,
            audio_bytes=audio_bytes,
            mime_type=payload.mime_type,
            content_service=content_service,
        )
        return VoiceToContentResponse(
            text=transcribe_res.text,
            summary=transcribe_res.summary,
            detected_intent=transcribe_res.detected_intent,
            job_id=job.id,
            job_status=job.status.value,
        )
    except InvalidAudioFormatError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except AudioPayloadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except VoiceTranscribeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


class VoiceTTSRequest(BaseModel):
    """Payload yêu cầu tạo file âm thanh giọng đọc tiếng Việt từ văn bản."""

    text: str = Field(
        ..., max_length=2000, description="Văn bản tiếng Việt cần chuyển thành giọng đọc"
    )
    voice: str = Field(
        default="vi-VN-HoaiMyNeural",
        description="Giọng đọc AI (vi-VN-HoaiMyNeural hoặc vi-VN-NamMinhNeural)",
    )
    rate: str = Field(default="+0%", description="Tốc độ đọc (+0%, +10%, -10%...)")


@router.post("/tts")
async def generate_speech_audio(
    payload: VoiceTTSRequest,
    workspace_id: WorkspaceDep,
):
    """Tạo file âm thanh giọng đọc tiếng Việt siêu tự nhiên 0 VNĐ bằng Edge-TTS."""
    import edge_tts

    clean_text = payload.text.strip()
    if not clean_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng cung cấp văn bản để tạo giọng đọc",
        )

    try:
        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=payload.voice,
            rate=payload.rate,
        )
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])

        audio_bytes = b"".join(chunks)
        if not audio_bytes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không thể tạo file âm thanh từ văn bản",
            )

        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi tạo giọng đọc AI: {exc}",
        ) from exc
