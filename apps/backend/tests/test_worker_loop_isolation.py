"""Kiểm tra worker không dùng chung connection pool qua nhiều event loop."""

import asyncio

from sqlalchemy import text

from adapters.persistence.db import session_scope
from worker.tasks import publish_run_due


def test_consecutive_worker_tasks_in_different_event_loops():
    """Hai task Celery / asyncio.run chạy nối tiếp trong cùng tiến trình không ném lỗi loop."""
    # Run task 1 in loop 1
    result1 = publish_run_due(limit=10)
    assert isinstance(result1, int)

    # Run task 2 in loop 2
    result2 = publish_run_due(limit=10)
    assert isinstance(result2, int)


def test_session_scope_across_multiple_asyncio_runs():
    """session_scope() chạy độc lập trong nhiều lần asyncio.run() không bị dính socket loop cũ."""
    async def _query_now() -> str:
        async with session_scope() as session:
            res = await session.execute(text("SELECT 1"))
            return str(res.scalar())

    # First asyncio.run
    out1 = asyncio.run(_query_now())
    assert out1 == "1"

    # Second asyncio.run (new loop)
    out2 = asyncio.run(_query_now())
    assert out2 == "1"
