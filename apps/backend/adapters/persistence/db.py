"""Async engine + session factory — nguồn kết nối Postgres duy nhất cho API/worker."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import get_settings

_engine: AsyncEngine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Commit-per-request: request thành công mới ghi thật, lỗi thì rollback hết."""
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
