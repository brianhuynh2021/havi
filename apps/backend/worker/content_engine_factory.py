"""Dựng ContentEngine trong worker.

Worker không có FastAPI dependency injection nên phải tự lắp — nhưng dùng đúng
những repository/adapter mà API dùng, không nhân đôi business rule (nguyên tắc
"API, worker và scheduler gọi cùng application service", SYSTEM_ARCHITECTURE.md §0).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from adapters.llm.anthropic import AnthropicProvider
from adapters.llm.gemini import GeminiProvider
from adapters.llm.openai import OpenAIProvider
from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.db import session_scope
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.content_engine import ContentEngine
from core.config import get_settings
from domain.policies.provider_router import ProviderRouter
from domain.ports.llm import LLMProvider


def build_provider_router() -> ProviderRouter:
    settings = get_settings()
    return ProviderRouter(
        {
            LLMProvider.GEMINI: GeminiProvider(settings),
            LLMProvider.ANTHROPIC: AnthropicProvider(settings),
            LLMProvider.OPENAI: OpenAIProvider(settings),
        }
    )


@asynccontextmanager
async def content_engine_scope() -> AsyncGenerator[ContentEngine]:
    """Một session cho cả job: commit khi xong, rollback nếu ném lỗi."""
    async with session_scope() as session:
        yield ContentEngine(
            content=ContentRepository(session),
            workspaces=WorkspaceRepository(session),
            profiles=BrandProfileRepository(session),
            media=MediaRepository(session),
            events=EventLogRepository(session),
            router=build_provider_router(),
        )
