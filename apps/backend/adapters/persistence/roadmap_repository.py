"""Repository cho Roadmap, Tasks, Evidence, Reviews (Havi 3.0)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import RoadmapStatus, TaskStatus
from domain.models.roadmap import EvidenceLog, Roadmap, RoadmapReview, RoadmapTask


class RoadmapRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Roadmap CRUD ---
    async def create_roadmap(
        self,
        *,
        workspace_id: UUID,
        goal_id: UUID,
        title: str,
        horizon_90d: str,
        horizon_30d: str,
        horizon_7d: str,
        version: int = 1,
        assumptions: list | None = None,
        confidence_score: float = 0.85,
        status: str = RoadmapStatus.ACTIVE.value,
    ) -> Roadmap:
        roadmap = Roadmap(
            workspace_id=workspace_id,
            goal_id=goal_id,
            title=title,
            horizon_90d=horizon_90d,
            horizon_30d=horizon_30d,
            horizon_7d=horizon_7d,
            version=version,
            assumptions=assumptions or [],
            confidence_score=confidence_score,
            status=status,
        )
        self._session.add(roadmap)
        await self._session.flush()
        return roadmap

    async def get_active_roadmap(
        self, *, workspace_id: UUID, goal_id: UUID | None = None
    ) -> Roadmap | None:
        stmt = select(Roadmap).where(
            Roadmap.workspace_id == workspace_id,
            Roadmap.status == RoadmapStatus.ACTIVE.value,
        )
        if goal_id:
            stmt = stmt.where(Roadmap.goal_id == goal_id)
        stmt = stmt.order_by(desc(Roadmap.version), desc(Roadmap.created_at)).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_roadmap_by_id(self, *, workspace_id: UUID, roadmap_id: UUID) -> Roadmap | None:
        stmt = select(Roadmap).where(
            Roadmap.workspace_id == workspace_id,
            Roadmap.id == roadmap_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def archive_existing_roadmaps(self, *, workspace_id: UUID, goal_id: UUID) -> None:
        stmt = select(Roadmap).where(
            Roadmap.workspace_id == workspace_id,
            Roadmap.goal_id == goal_id,
            Roadmap.status == RoadmapStatus.ACTIVE.value,
        )
        result = await self._session.execute(stmt)
        for rm in result.scalars().all():
            rm.status = RoadmapStatus.SUPERSEDED.value
        await self._session.flush()

    async def list_roadmap_history(
        self, *, workspace_id: UUID, goal_id: UUID | None = None
    ) -> list[Roadmap]:
        stmt = select(Roadmap).where(Roadmap.workspace_id == workspace_id)
        if goal_id:
            stmt = stmt.where(Roadmap.goal_id == goal_id)
        stmt = stmt.order_by(desc(Roadmap.version), desc(Roadmap.created_at))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # --- Tasks CRUD ---

    async def create_task(
        self,
        *,
        workspace_id: UUID,
        roadmap_id: UUID,
        goal_id: UUID,
        title: str,
        why_this_is_next: str,
        done_rule: str,
        description: str | None = None,
        time_estimate_minutes: int = 30,
        owner_type: str = "collaborative",
        capability_module: str = "manual",
        inputs_needed: str | None = None,
        fallback_action: str | None = None,
        scheduled_date: datetime | None = None,
        order_index: int = 0,
    ) -> RoadmapTask:
        task = RoadmapTask(
            workspace_id=workspace_id,
            roadmap_id=roadmap_id,
            goal_id=goal_id,
            title=title,
            why_this_is_next=why_this_is_next,
            done_rule=done_rule,
            description=description,
            time_estimate_minutes=time_estimate_minutes,
            owner_type=owner_type,
            capability_module=capability_module,
            inputs_needed=inputs_needed,
            fallback_action=fallback_action,
            scheduled_date=scheduled_date,
            order_index=order_index,
            status=TaskStatus.PENDING.value,
        )
        self._session.add(task)
        await self._session.flush()
        return task

    async def list_tasks_by_roadmap(
        self, *, workspace_id: UUID, roadmap_id: UUID
    ) -> list[RoadmapTask]:
        stmt = (
            select(RoadmapTask)
            .where(
                RoadmapTask.workspace_id == workspace_id,
                RoadmapTask.roadmap_id == roadmap_id,
            )
            .order_by(RoadmapTask.order_index, RoadmapTask.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_next_recommended_task(
        self, *, workspace_id: UUID, roadmap_id: UUID
    ) -> RoadmapTask | None:
        stmt = (
            select(RoadmapTask)
            .where(
                RoadmapTask.workspace_id == workspace_id,
                RoadmapTask.roadmap_id == roadmap_id,
                RoadmapTask.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]),
            )
            .order_by(RoadmapTask.order_index, RoadmapTask.created_at)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_task_by_id(self, *, workspace_id: UUID, task_id: UUID) -> RoadmapTask | None:
        stmt = select(RoadmapTask).where(
            RoadmapTask.workspace_id == workspace_id,
            RoadmapTask.id == task_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_task(
        self,
        task: RoadmapTask,
        *,
        status: str | None = None,
        completed_at: datetime | None = None,
        evidence_notes: str | None = None,
        fallback_action: str | None = None,
    ) -> RoadmapTask:
        if status is not None:
            task.status = status
        if completed_at is not None:
            task.completed_at = completed_at
        if evidence_notes is not None:
            task.evidence_notes = evidence_notes
        if fallback_action is not None:
            task.fallback_action = fallback_action
        await self._session.flush()
        return task

    # --- Evidence CRUD ---
    async def create_evidence(
        self,
        *,
        workspace_id: UUID,
        goal_id: UUID,
        value_text: str,
        task_id: UUID | None = None,
        source: str = "manual_checkin",
        evidence_type: str = "note",
        value_number: float | None = None,
        media_asset_id: UUID | None = None,
        confidence: float = 1.0,
    ) -> EvidenceLog:
        evidence = EvidenceLog(
            workspace_id=workspace_id,
            goal_id=goal_id,
            task_id=task_id,
            source=source,
            evidence_type=evidence_type,
            value_text=value_text,
            value_number=value_number,
            media_asset_id=media_asset_id,
            confidence=confidence,
        )
        self._session.add(evidence)
        await self._session.flush()
        return evidence

    async def list_evidence(
        self, *, workspace_id: UUID, goal_id: UUID | None = None
    ) -> list[EvidenceLog]:
        stmt = select(EvidenceLog).where(EvidenceLog.workspace_id == workspace_id)
        if goal_id:
            stmt = stmt.where(EvidenceLog.goal_id == goal_id)
        stmt = stmt.order_by(desc(EvidenceLog.created_at))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # --- Review CRUD ---
    async def create_review(
        self,
        *,
        workspace_id: UUID,
        goal_id: UUID,
        roadmap_id: UUID,
        completed_summary: str,
        evidence_summary: str,
        obstacles_summary: str,
        decision: str,
        replan_diff: dict | None = None,
        user_accepted: bool = False,
    ) -> RoadmapReview:
        review = RoadmapReview(
            workspace_id=workspace_id,
            goal_id=goal_id,
            roadmap_id=roadmap_id,
            review_date=datetime.now(UTC),
            completed_summary=completed_summary,
            evidence_summary=evidence_summary,
            obstacles_summary=obstacles_summary,
            decision=decision,
            replan_diff=replan_diff,
            user_accepted=user_accepted,
        )
        self._session.add(review)
        await self._session.flush()
        return review

    async def list_reviews(
        self, *, workspace_id: UUID, goal_id: UUID | None = None
    ) -> list[RoadmapReview]:
        stmt = select(RoadmapReview).where(RoadmapReview.workspace_id == workspace_id)
        if goal_id:
            stmt = stmt.where(RoadmapReview.goal_id == goal_id)
        stmt = stmt.order_by(desc(RoadmapReview.review_date))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
