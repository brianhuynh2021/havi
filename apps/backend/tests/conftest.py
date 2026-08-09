"""Fixtures dùng chung — test DB-backed dùng Postgres thật (docker compose up -d ở
root repo), mỗi test chạy trong 1 transaction rồi rollback, không để lại dữ liệu.
"""

import os

# Tắt rate limit cho toàn bộ test suite, TRƯỚC khi `core.config` được import lần
# đầu (Settings đọc env lúc khởi tạo và `get_settings` có lru_cache).
#
# Lý do tắt: rate limit đếm trong Redis, mà test suite gọi `/auth/login` hàng
# chục lần trong vài giây — thật hơn nhịp người dùng nhiều lần. Không tắt thì
# test thứ 11 bắt đầu đỏ, và đỏ theo thứ tự chạy nên rất khó truy.
#
# Bản thân cơ chế rate limit vẫn được test — ở `test_rate_limit.py`, bằng cách
# dựng limiter trực tiếp với Redis thật thay vì đi qua HTTP.
os.environ.setdefault("HAVI_DISABLE_RATE_LIMIT", "true")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from adapters.persistence.db import _engine, get_db_session  # noqa: E402
from api.main import create_app  # noqa: E402


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
