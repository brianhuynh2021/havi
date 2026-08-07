"""Gemini adapter — provider ưu tiên (SYSTEM_ARCHITECTURE.md §5.1).

Gọi REST trực tiếp bằng httpx thay vì thêm google-genai SDK: chỉ cần một endpoint
`generateContent`, và giữ dependency mỏng thì adapter cho provider khác cũng cùng
một khuôn (không mỗi provider một SDK với vòng đời riêng).

Dùng structured output native của Gemini (`responseMimeType` +
`responseSchema`) nên không phải cầu xin model trả JSON đúng trong prompt.
"""

import time

import httpx

from core.config import Settings
from domain.ports.llm import (
    LLMPermanentError,
    LLMProvider,
    LLMProviderPort,
    LLMRequest,
    LLMResponse,
    LLMTransientError,
)

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
#: Retry được: rate limit và lỗi phía server.
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class GeminiProvider(LLMProviderPort):
    def __init__(self, settings: Settings, *, timeout_seconds: float = 60.0) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_model
        self._timeout = timeout_seconds

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.GEMINI

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "contents": [{"parts": [{"text": request.user_prompt}]}],
            "systemInstruction": {"parts": [{"text": request.system_prompt}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _to_gemini_schema(request.output_schema),
                "maxOutputTokens": request.max_output_tokens,
            },
        }
        url = f"{_BASE_URL}/{self._model}:generateContent"
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    url, params={"key": self._api_key}, json=payload
                )
        except httpx.TimeoutException as exc:
            raise LLMTransientError(self.provider, f"timeout sau {self._timeout}s") from exc
        except httpx.HTTPError as exc:
            raise LLMTransientError(self.provider, f"lỗi kết nối: {exc}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        if response.status_code in _TRANSIENT_STATUSES:
            raise LLMTransientError(
                self.provider, f"HTTP {response.status_code}: {response.text[:200]}"
            )
        if response.status_code >= 400:
            raise LLMPermanentError(
                self.provider, f"HTTP {response.status_code}: {response.text[:200]}"
            )

        body = response.json()
        candidates = body.get("candidates") or []
        if not candidates:
            # Prompt bị safety filter chặn — retry y nguyên sẽ lại bị chặn.
            reason = body.get("promptFeedback", {}).get("blockReason", "không có candidate")
            raise LLMPermanentError(self.provider, f"không có output: {reason}")

        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts)
        usage = body.get("usageMetadata", {})
        return LLMResponse(
            text=text,
            provider=self.provider,
            model=self._model,
            tokens_in=usage.get("promptTokenCount", 0),
            tokens_out=usage.get("candidatesTokenCount", 0),
            latency_ms=latency_ms,
        )


def _to_gemini_schema(schema: dict) -> dict:
    """Bỏ các key JSON Schema mà responseSchema của Gemini không nhận.

    Gemini dùng tập con của OpenAPI schema — gửi `additionalProperties`,
    `$schema`, `title`… sẽ bị 400. Lọc đệ quy thay vì bắt caller phải biết
    provider nào chấp nhận key nào.
    """
    unsupported = {"additionalProperties", "$schema", "title", "default", "examples"}
    if not isinstance(schema, dict):
        return schema
    cleaned: dict = {}
    for key, value in schema.items():
        if key in unsupported:
            continue
        if isinstance(value, dict):
            cleaned[key] = _to_gemini_schema(value)
        elif isinstance(value, list):
            cleaned[key] = [_to_gemini_schema(v) if isinstance(v, dict) else v for v in value]
        else:
            cleaned[key] = value
    return cleaned
