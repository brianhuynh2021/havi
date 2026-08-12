"""Anthropic adapter — fallback thứ nhất khi Gemini lỗi.

Dùng REST + httpx (không thêm SDK) để mọi adapter cùng một khuôn — xem lý do ở
`gemini.py`. Structured output qua `output_config.format` với json_schema.
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

_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504, 529})


def _sanitize_schema_for_anthropic(schema: dict) -> dict:
    """Anthropic structured output (output_config.format) yêu cầu mọi object schema
    phải chỉ định rõ `additionalProperties: False`.
    """
    if not isinstance(schema, dict):
        return schema
    res = dict(schema)
    if res.get("type") == "object" or "properties" in res:
        if "type" not in res:
            res["type"] = "object"
        res.setdefault("additionalProperties", False)
    if "properties" in res and isinstance(res["properties"], dict):
        res["properties"] = {
            k: _sanitize_schema_for_anthropic(v) for k, v in res["properties"].items()
        }
    if "items" in res and isinstance(res["items"], dict):
        res["items"] = _sanitize_schema_for_anthropic(res["items"])
    for key in ("$defs", "definitions"):
        if key in res and isinstance(res[key], dict):
            res[key] = {k: _sanitize_schema_for_anthropic(v) for k, v in res[key].items()}
    return res


class AnthropicProvider(LLMProviderPort):
    def __init__(self, settings: Settings, *, timeout_seconds: float = 60.0) -> None:
        self._api_key = settings.anthropic_api_key
        self._model = settings.anthropic_model
        self._timeout = timeout_seconds

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.ANTHROPIC

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        sanitized_schema = _sanitize_schema_for_anthropic(request.output_schema)
        payload = {
            "model": self._model,
            "max_tokens": request.max_output_tokens,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.user_prompt}],
            "output_config": {
                "format": {"type": "json_schema", "schema": sanitized_schema}
            },
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _API_VERSION,
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
        # Safety classifier từ chối: HTTP 200 nhưng stop_reason="refusal" và
        # content rỗng — đọc content[0] mà không kiểm trước sẽ IndexError.
        if body.get("stop_reason") == "refusal":
            category = (body.get("stop_details") or {}).get("category", "không rõ")
            raise LLMPermanentError(self.provider, f"bị từ chối ({category})")

        text = "".join(
            block.get("text", "")
            for block in body.get("content", [])
            if block.get("type") == "text"
        )
        usage = body.get("usage", {})
        return LLMResponse(
            text=text,
            provider=self.provider,
            model=body.get("model", self._model),
            tokens_in=usage.get("input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
            latency_ms=latency_ms,
        )
