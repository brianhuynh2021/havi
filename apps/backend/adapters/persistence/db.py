"""Async engine + session factory — nguồn kết nối Postgres duy nhất cho API/worker."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from core.config import get_settings

_settings = get_settings()

#: Engine cho FastAPI app (chạy trong cùng một long-lived event loop)
_engine: AsyncEngine = create_async_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)

#: Engine cho worker / scheduler / scripts (mỗi task chạy trong asyncio.run() riêng)
#: Dùng NullPool để không giữ connection socket gắn với event loop đã kết thúc.
_worker_engine: AsyncEngine = create_async_engine(
    _settings.database_url,
    poolclass=NullPool,
    pool_pre_ping=True,
)
_worker_session_factory = async_sessionmaker(_worker_engine, expire_on_commit=False)


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


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession]:
    """Cho worker/scheduler — chỗ không có FastAPI dependency injection.

    Dùng NullPool engine để an toàn qua nhiều lần asyncio.run() khác nhau.
    """
    async with _worker_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
