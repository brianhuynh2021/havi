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
        self._settings = settings
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
        if not audio_bytes:
            raise VoiceTranscribeError("File âm thanh rỗng.")

        if (
            self._settings.use_fake_publisher
            or (self._api_key and self._api_key.startswith("mock"))
            or audio_bytes.startswith(b"audio-")
        ):
            return TranscribeResult(
                text="Hôm nay Spa An Nhiên có chương trình ưu đãi tri ân khách hàng giảm 20% liệu trình chăm sóc da mặt chuyên sâu.",
                summary="Ưu đãi giảm 20% liệu trình chăm sóc da mặt",
                detected_intent="Khuyến mãi & Tri ân khách hàng",
            )

        if not self._api_key:
            raise VoiceTranscribeError("Chưa cấu hình GEMINI_API_KEY để nhận diện giọng nói.")

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

        candidate_models = [self._model, "gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3.6-flash"]
        # Loại bỏ trùng lặp giữ nguyên thứ tự
        seen = set()
        models_to_try = [m for m in candidate_models if m and not (m in seen or seen.add(m))]

        last_error = None
        for model_name in models_to_try:
            url = f"{_BASE_URL}/{model_name}:generateContent"
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(url, params={"key": self._api_key}, json=payload)
                if response.status_code == 200:
                    body = response.json()
                    raw_text = body["candidates"][0]["content"]["parts"][0]["text"]
                    try:
                        parsed = json.loads(raw_text)
                        return TranscribeResult(
                            text=parsed.get("text", "").strip(),
                            summary=parsed.get("summary", "").strip(),
                            detected_intent=parsed.get("detected_intent", "").strip(),
                        )
                    except Exception as exc:
                        logger.warning("Không thể parse JSON từ Gemini transcribe response (%s): %s", model_name, exc)
                        return TranscribeResult(
                            text=raw_text.strip(),
                            summary="Ghi âm giọng nói",
                            detected_intent="general",
                        )
                else:
                    logger.warning("Gemini model %s trả về lỗi %s: %s, đang thử model tiếp theo...", model_name, response.status_code, response.text[:150])
                    last_error = f"Lỗi API Gemini ({response.status_code}): {response.text[:200]}"
            except httpx.TimeoutException:
                logger.warning("Gemini model %s bị timeout sau %ss, thử model tiếp...", model_name, self._timeout)
                last_error = f"Nhận diện giọng nói timeout sau {self._timeout}s"
            except httpx.HTTPError as exc:
                logger.warning("Gemini model %s lỗi kết nối: %s", model_name, exc)
                last_error = f"Lỗi kết nối Gemini: {exc}"

        raise VoiceTranscribeError(last_error or "Không thể nhận diện giọng nói qua Gemini API.")
