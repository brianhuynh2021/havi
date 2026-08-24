"""Application Service cho Goal Management (Havi 3.0)."""

from datetime import datetime
from uuid import UUID

from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.goal_repository import GoalRepository
from core.events import EventLogEntry
from domain.models.goal import Goal


class GoalService:
    def __init__(
        self,
        *,
        goal_repo: GoalRepository,
        event_repo: EventLogRepository | None = None,
    ) -> None:
        self._goals = goal_repo
        self._events = event_repo

    async def create_goal(
        self,
        *,
        workspace_id: UUID,
        title: str,
        category: str,
        evidence_definition: str,
        description: str | None = None,
        target_deadline: datetime | None = None,
        weekly_capacity_hours: int = 10,
        constraints: dict | None = None,
    ) -> Goal:
        goal = await self._goals.create(
            workspace_id=workspace_id,
            title=title,
            category=category,
            evidence_definition=evidence_definition,
            description=description,
            target_deadline=target_deadline,
            weekly_capacity_hours=weekly_capacity_hours,
            constraints=constraints,
        )
        if self._events:
            await self._events.record(
                EventLogEntry(
                    workspace_id=workspace_id,
                    job_kind="goal.created",
                    input_summary=f"Category: {category}",
                    output_summary=f"Goal created: {title}",
                )
            )
        return goal

    async def get_active_goal(self, *, workspace_id: UUID) -> Goal | None:
        return await self._goals.get_active_goal(workspace_id=workspace_id)

    async def get_goal(self, *, workspace_id: UUID, goal_id: UUID) -> Goal | None:
        return await self._goals.get_by_id(workspace_id=workspace_id, goal_id=goal_id)

    async def list_goals(self, *, workspace_id: UUID) -> list[Goal]:
        return await self._goals.list_by_workspace(workspace_id=workspace_id)

    async def update_goal(
        self,
        *,
        workspace_id: UUID,
        goal_id: UUID,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        evidence_definition: str | None = None,
        target_deadline: datetime | None = None,
        weekly_capacity_hours: int | None = None,
        constraints: dict | None = None,
    ) -> Goal | None:
        goal = await self._goals.get_by_id(workspace_id=workspace_id, goal_id=goal_id)
        if not goal:
            return None
        return await self._goals.update(
            goal,
            title=title,
            description=description,
            status=status,
            evidence_definition=evidence_definition,
            target_deadline=target_deadline,
            weekly_capacity_hours=weekly_capacity_hours,
            constraints=constraints,
        )

    async def archive_goal(self, *, workspace_id: UUID, goal_id: UUID) -> bool:
        goal = await self._goals.get_by_id(workspace_id=workspace_id, goal_id=goal_id)
        if not goal:
            return False
        await self._goals.update(goal, status="abandoned")
        return True
