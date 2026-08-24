"""Repository cho Goal — Quản lý mục tiêu workspace (Havi 3.0)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import GoalStatus
from domain.models.goal import Goal


class GoalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
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
        # Deactivate previous active goals
        existing_active = await self._session.execute(
            select(Goal).where(
                Goal.workspace_id == workspace_id,
                Goal.status == GoalStatus.ACTIVE.value,
            )
        )
        for old_g in existing_active.scalars().all():
            old_g.status = GoalStatus.ABANDONED.value

        goal = Goal(
            workspace_id=workspace_id,
            title=title,
            category=category,
            evidence_definition=evidence_definition,
            description=description,
            target_deadline=target_deadline,
            weekly_capacity_hours=weekly_capacity_hours,
            constraints=constraints or {},
            status=GoalStatus.ACTIVE.value,
        )
        self._session.add(goal)
        await self._session.flush()
        return goal

    async def get_by_id(self, *, workspace_id: UUID, goal_id: UUID) -> Goal | None:
        stmt = select(Goal).where(Goal.workspace_id == workspace_id, Goal.id == goal_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_goal(self, *, workspace_id: UUID) -> Goal | None:
        stmt = (
            select(Goal)
            .where(
                Goal.workspace_id == workspace_id,
                Goal.status == GoalStatus.ACTIVE.value,
            )
            .order_by(desc(Goal.created_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(self, *, workspace_id: UUID) -> list[Goal]:
        stmt = select(Goal).where(Goal.workspace_id == workspace_id).order_by(desc(Goal.created_at))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        goal: Goal,
        *,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        evidence_definition: str | None = None,
        target_deadline: datetime | None = None,
        weekly_capacity_hours: int | None = None,
        constraints: dict | None = None,
    ) -> Goal:
        if title is not None:
            goal.title = title
        if description is not None:
            goal.description = description
        if status is not None:
            goal.status = status
        if evidence_definition is not None:
            goal.evidence_definition = evidence_definition
        if target_deadline is not None:
            goal.target_deadline = target_deadline
        if weekly_capacity_hours is not None:
            goal.weekly_capacity_hours = weekly_capacity_hours
        if constraints is not None:
            goal.constraints = constraints
        await self._session.flush()
        return goal
