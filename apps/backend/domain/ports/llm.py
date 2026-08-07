"""Port cho model provider — domain chỉ biết interface này, không biết Gemini/OpenAI.

Thiết kế theo SYSTEM_ARCHITECTURE.md §5.1: không phụ thuộc một provider duy nhất,
một lần Gemini/Anthropic/OpenAI sập không được làm tê liệt Content Engine.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class LLMProvider(StrEnum):
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class LLMRequest:
    system_prompt: str
    user_prompt: str
    #: JSON Schema mà output phải thoả — provider nào hỗ trợ structured output thì
    #: truyền xuống, không thì đưa vào prompt.
    output_schema: dict
    max_output_tokens: int = 8192


@dataclass
class LLMResponse:
    text: str
    provider: LLMProvider
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int


class LLMError(Exception):
    """Base cho mọi lỗi từ provider."""

    def __init__(self, provider: LLMProvider, message: str) -> None:
        super().__init__(f"[{provider}] {message}")
        self.provider = provider


class LLMTransientError(LLMError):
    """Rate limit, timeout, 5xx — đáng thử provider khác hoặc retry."""


class LLMPermanentError(LLMError):
    """Sai API key, prompt bị từ chối, request không hợp lệ — thử lại vô nghĩa."""


class LLMProviderPort(ABC):
    """Một provider cụ thể. Adapter chỉ chuyển đổi I/O, không quyết định fallback."""

    @property
    @abstractmethod
    def provider(self) -> LLMProvider: ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """False khi thiếu API key — router bỏ qua provider này thay vì gọi rồi lỗi."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse: ...
