"""ProviderRouter — quyết định thử provider nào, theo thứ tự nào.

Code thường, không phải LLM. Ba lý do fallback (SYSTEM_ARCHITECTURE.md §5.1):

1. **Outage/lỗi/timeout** — provider trả `LLMTransientError` → thử provider kế tiếp.
2. **Cost routing** — `preferred_order` truyền từ ngoài vào, nên gói giá khác nhau
   map sang thứ tự khác nhau mà router không cần biết gì về pricing.
3. **Chất lượng output không đạt** — `validate` trả lỗi → thử provider khác thay
   vì retry cùng provider với cùng prompt (retry y nguyên thì hầu như ra cùng kết quả).

Router **không** biết schema hay banned-claims; nó chỉ gọi `validate` do caller
truyền vào. Nhờ vậy Content Engine đổi rule validation mà không phải sửa router.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar

from core.metrics import llm_duration_seconds, llm_requests_total
from domain.policies.circuit_breaker import CircuitOpenError
from domain.policies.circuit_breaker import registry as breaker_registry
from domain.ports.llm import (
    LLMPermanentError,
    LLMProvider,
    LLMProviderPort,
    LLMRequest,
    LLMResponse,
    LLMTransientError,
)

logger = logging.getLogger("havi.provider_router")

T = TypeVar("T")

#: Gemini ưu tiên. Xem SYSTEM_ARCHITECTURE.md §5.1.
DEFAULT_PROVIDER_ORDER: tuple[LLMProvider, ...] = (
    LLMProvider.GEMINI,
    LLMProvider.ANTHROPIC,
    LLMProvider.OPENAI,
)


class OutputValidationError(Exception):
    """Validator từ chối output — router coi đây là lý do đổi provider."""


@dataclass
class Attempt:
    provider: LLMProvider
    ok: bool
    #: Lý do chuyển provider: `transient`, `permanent`, `invalid_output`, hoặc None nếu ok.
    failure_kind: str | None = None
    failure_detail: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0


@dataclass
class RouterResult[T]:
    value: T
    response: LLMResponse
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def served_by(self) -> LLMProvider:
        return self.response.provider

    @property
    def total_tokens_in(self) -> int:
        return sum(a.tokens_in for a in self.attempts)

    @property
    def total_tokens_out(self) -> int:
        return sum(a.tokens_out for a in self.attempts)


class AllProvidersFailed(Exception):
    def __init__(self, attempts: list[Attempt]) -> None:
        if not attempts:
            summary = "không có provider nào được cấu hình (thiếu API key)"
        else:
            # Kèm `failure_detail`, không chỉ `failure_kind`: "transient" không cho
            # biết là 429, timeout hay 503 — mà reason này đi vào
            # `content_jobs.failure_reason` để support tra lỗi (ROADMAP.md Gate E:
            # mọi failed job phải có reason và cách recovery rõ).
            summary = "; ".join(
                f"{a.provider}={a.failure_kind}"
                + (f" ({a.failure_detail})" if a.failure_detail else "")
                for a in attempts
            )
        super().__init__(f"Mọi provider đều thất bại: {summary}")
        self.attempts = attempts


class ProviderRouter:
    def __init__(self, providers: dict[LLMProvider, LLMProviderPort]) -> None:
        self._providers = providers

    def available(self, order: tuple[LLMProvider, ...]) -> list[LLMProviderPort]:
        """Bỏ qua provider thiếu API key — gọi rồi lỗi thì tốn latency vô ích."""
        return [
            self._providers[p]
            for p in order
            if p in self._providers and self._providers[p].is_configured
        ]

    async def generate(
        self,
        request: LLMRequest,
        *,
        validate: Callable[[str], T],
        order: tuple[LLMProvider, ...] = DEFAULT_PROVIDER_ORDER,
    ) -> RouterResult[T]:
        """`validate` parse + kiểm output; ném `OutputValidationError` để đổi provider."""
        attempts: list[Attempt] = []
        candidates = self.available(order)
        if not candidates:
            raise AllProvidersFailed(attempts)

        for provider_port in candidates:
            provider = provider_port.provider
            breaker = breaker_registry.get(f"llm.{provider}")
            started = time.perf_counter()
            try:
                # Breaker chặn *trước* khi mở kết nối. Đây là toàn bộ giá trị của
                # nó: provider đang chết thì không tốn một giây timeout nào nữa,
                # request rơi xuống provider kế tiếp gần như tức thì.
                breaker.raise_if_open()
                response = await provider_port.generate(request)
            except CircuitOpenError as exc:
                # `failure_kind` riêng, không gộp vào "transient": khi truy lỗi,
                # "breaker đang mở" và "provider vừa trả 503" dẫn tới hai kết
                # luận khác nhau — cái sau là sự cố mới, cái trước là hệ quả đã
                # biết của sự cố cũ.
                attempts.append(
                    Attempt(
                        provider,
                        ok=False,
                        failure_kind="circuit_open",
                        failure_detail=str(exc),
                    )
                )
                llm_requests_total.labels(
                    provider=str(provider), outcome="circuit_open"
                ).inc()
                logger.warning("provider %s bị breaker chặn: %s", provider, exc)
                continue
            except LLMTransientError as exc:
                breaker.record_failure()
                llm_requests_total.labels(provider=str(provider), outcome="transient").inc()
                llm_duration_seconds.labels(provider=str(provider)).observe(
                    time.perf_counter() - started
                )
                attempts.append(
                    Attempt(provider, ok=False, failure_kind="transient", failure_detail=str(exc))
                )
                logger.warning("provider %s transient failure: %s", provider, exc)
                continue
            except LLMPermanentError as exc:
                # Sai key/prompt bị từ chối: thử provider khác vẫn có ý nghĩa (key
                # provider khác có thể đúng), nhưng không retry chính provider này.
                #
                # **Không** gọi `record_failure`: lỗi permanent là lỗi của input,
                # không phải của upstream. Đếm nó sẽ mở breaker trên một provider
                # hoàn toàn khoẻ chỉ vì người dùng gửi prompt bị policy từ chối.
                llm_requests_total.labels(provider=str(provider), outcome="permanent").inc()
                llm_duration_seconds.labels(provider=str(provider)).observe(
                    time.perf_counter() - started
                )
                attempts.append(
                    Attempt(provider, ok=False, failure_kind="permanent", failure_detail=str(exc))
                )
                logger.warning("provider %s permanent failure: %s", provider, exc)
                continue

            try:
                result = validate(response.text)
            except OutputValidationError as exc:
                # Upstream *đã* trả lời được, chỉ nội dung không đạt. Với sức khoẻ
                # kết nối thì đây là thành công — coi là lỗi sẽ mở breaker vì
                # chất lượng prompt, và chặn mất một provider vẫn đang phục vụ tốt.
                breaker.record_success()
                llm_requests_total.labels(
                    provider=str(provider), outcome="invalid_output"
                ).inc()
                llm_duration_seconds.labels(provider=str(provider)).observe(
                    time.perf_counter() - started
                )
                attempts.append(
                    Attempt(
                        provider,
                        ok=False,
                        failure_kind="invalid_output",
                        failure_detail=str(exc),
                        tokens_in=response.tokens_in,
                        tokens_out=response.tokens_out,
                        latency_ms=response.latency_ms,
                    )
                )
                logger.warning("provider %s output invalid: %s", provider, exc)
                continue

            breaker.record_success()
            llm_requests_total.labels(provider=str(provider), outcome="ok").inc()
            llm_duration_seconds.labels(provider=str(provider)).observe(
                time.perf_counter() - started
            )
            attempts.append(
                Attempt(
                    provider,
                    ok=True,
                    tokens_in=response.tokens_in,
                    tokens_out=response.tokens_out,
                    latency_ms=response.latency_ms,
                )
            )
            return RouterResult(value=result, response=response, attempts=attempts)

        raise AllProvidersFailed(attempts)
