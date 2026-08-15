"""Test suite cho Celery scheduler task crm_lifecycle_nudges."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

from scheduler.tasks import crm_lifecycle_nudges


def test_scheduler_crm_lifecycle_nudges_task_wiring(monkeypatch):
    calls: list[str] = []

    class _FakeWorkspace:
        id = "mock_ws_id"

    class _FakeWorkspaceRepo:
        def __init__(self, session):
            pass

        async def list_all(self):
            calls.append("list_all")
            return [_FakeWorkspace()]

    class _FakeNudgeService:
        def __init__(self, **kwargs):
            pass

        async def scan_and_generate_nudges(self, *, workspace_id, inactive_days):
            calls.append(f"scan_{workspace_id}")
            return ["mock_nudge_1", "mock_nudge_2"]

    @asynccontextmanager
    async def _fake_session_scope():
        yield AsyncMock()

    monkeypatch.setattr("adapters.persistence.db.session_scope", _fake_session_scope)
    monkeypatch.setattr(
        "adapters.persistence.workspace_repository.WorkspaceRepository", _FakeWorkspaceRepo
    )
    monkeypatch.setattr(
        "application.services.crm_nudge_service.CrmNudgeService", _FakeNudgeService
    )

    total = crm_lifecycle_nudges()
    assert total == 2
    assert "list_all" in calls
    assert "scan_mock_ws_id" in calls
