"""Gemini Multimodal Audio Transcriber — nhận diện âm thanh giọng nói tiếng Việt."""

import base64
import json
import logging
from typing import Any

import httpx

from core.config import Settings
from domain.ports.voice_transcriber import (
    TranscribeResult,
    VoiceTranscribeError,
    VoiceTranscriberPort,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiVoiceTranscriber(VoiceTranscriberPort):
    """Sử dụng Gemini Multimodal Audio để chuyển giọng nói tiếng Việt thành văn bản."""

    def __init__(self, settings: Settings, *, timeout_seconds: float = 60.0) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_model or "gemini-1.5-flash"
        self._timeout = timeout_seconds

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str,
        *,
        language: str = "vi",
    ) -> TranscribeResult:
        if not self._api_key:
            raise VoiceTranscribeError("Chưa cấu hình GEMINI_API_KEY để nhận diện giọng nói.")

        if not audio_bytes:
            raise VoiceTranscribeError("File âm thanh rỗng.")

        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

        system_instruction = (
            "Bạn là chuyên viên chuyển đổi âm thanh giọng nói tiếng Việt sang văn bản cho chủ tiệm doanh nghiệp Havi. "
            "Nhiệm vụ: Chuyển toàn bộ nội dung giọng nói của chủ tiệm sang tiếng Việt chính xác, đầy đủ dấu, "
            "loại bỏ tiếng ậm ừ nhưng giữ nguyên 100% các ý tưởng, tên dịch vụ/sản phẩm, giá tiền, địa chỉ, ưu đãi. "
            "Trả về duy nhất định dạng JSON có cấu trúc: "
            '{"text": "toàn bộ lời nói chuẩn hoá", "summary": "tóm tắt ý chính ngắn gọn", "detected_intent": "ý định (khuyến mãi, giới thiệu dịch vụ, tuyển dụng, kể chuyện nghề...)"}'
        )

        user_prompt = "Hãy nghe đoạn ghi âm giọng nói này và chuyển thành văn bản tiếng Việt theo đúng hướng dẫn."

        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": b64_audio,
                            }
                        },
                        {"text": user_prompt},
                    ]
                }
            ],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }

        url = f"{_BASE_URL}/{self._model}:generateContent"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, params={"key": self._api_key}, json=payload)
        except httpx.TimeoutException as exc:
            raise VoiceTranscribeError(f"Nhận diện giọng nói timeout sau {self._timeout}s") from exc
        except httpx.HTTPError as exc:
            raise VoiceTranscribeError(f"Lỗi kết nối Gemini: {exc}") from exc

        if response.status_code != 200:
            logger.error("Gemini audio transcription failed (%s): %s", response.status_code, response.text)
            raise VoiceTranscribeError(f"Lỗi API Gemini ({response.status_code}): {response.text[:200]}")

        try:
            body = response.json()
            raw_text = body["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            return TranscribeResult(
                text=parsed.get("text", "").strip(),
                summary=parsed.get("summary", "").strip(),
                detected_intent=parsed.get("detected_intent", "").strip(),
            )
        except Exception as exc:
            logger.warning("Không thể parse JSON từ Gemini transcribe response: %s", exc)
            # Fallback nếu text thuần
            return TranscribeResult(
                text=raw_text.strip() if "raw_text" in locals() else "",
                summary="Ghi âm giọng nói",
                detected_intent="general",
            )
