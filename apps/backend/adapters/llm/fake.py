"""Fake provider — để test Content Engine không cần API key thật.

Đúng cách ROADMAP.md §10 nói: "provider interface + dev stub". Test dùng cái này
để kiểm luồng (fallback, validation, idempotency) mà không tốn tiền và không phụ
thuộc mạng; adapter thật (Gemini) chỉ verify được khi có key.
"""

from collections.abc import Callable

from domain.ports.llm import (
    LLMProvider,
    LLMProviderPort,
    LLMRequest,
    LLMResponse,
)


class FakeProvider(LLMProviderPort):
    def __init__(
        self,
        *,
        provider: LLMProvider = LLMProvider.GEMINI,
        response_text: str | Callable[[LLMRequest], str] = "{}",
        error: Exception | None = None,
        configured: bool = True,
        tokens_in: int = 100,
        tokens_out: int = 200,
    ) -> None:
        self._provider = provider
        self._response_text = response_text
        self._error = error
        self._configured = configured
        self._tokens_in = tokens_in
        self._tokens_out = tokens_out
        self.calls: list[LLMRequest] = []

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        text = (
            self._response_text(request)
            if callable(self._response_text)
            else self._response_text
        )
        return LLMResponse(
            text=text,
            provider=self._provider,
            model=f"fake-{self._provider}",
            tokens_in=self._tokens_in,
            tokens_out=self._tokens_out,
            latency_ms=1,
        )
