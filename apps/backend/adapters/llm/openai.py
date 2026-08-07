"""OpenAI adapter — fallback thứ hai.

REST + httpx như hai adapter kia. Structured output qua
`response_format: json_schema` với `strict: true`.
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

_URL = "https://api.openai.com/v1/chat/completions"
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class OpenAIProvider(LLMProviderPort):
    def __init__(self, settings: Settings, *, timeout_seconds: float = 60.0) -> None:
        self._api_key = settings.openai_api_key
        self._model = settings.openai_model
        self._timeout = timeout_seconds

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OPENAI

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self._model,
            "max_completion_tokens": request.max_output_tokens,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "havi_drafts",
                    "strict": True,
                    "schema": request.output_schema,
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
        }
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(_URL, headers=headers, json=payload)
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
        choices = body.get("choices") or []
        if not choices:
            raise LLMPermanentError(self.provider, "không có choice trong response")
        message = choices[0].get("message", {})
        if message.get("refusal"):
            raise LLMPermanentError(self.provider, f"bị từ chối: {message['refusal'][:120]}")

        usage = body.get("usage", {})
        return LLMResponse(
            text=message.get("content") or "",
            provider=self.provider,
            model=body.get("model", self._model),
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
        )
