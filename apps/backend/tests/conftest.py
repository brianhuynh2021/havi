"""Fixtures dùng chung — test DB-backed dùng Postgres thật (docker compose up -d ở
root repo), mỗi test chạy trong 1 transaction rồi rollback, không để lại dữ liệu.
"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.db import _engine, get_db_session
from api.main import create_app


@pytest_asyncio.fixture
async def db_session():
    async with _engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    app = create_app()

    async def _override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()
