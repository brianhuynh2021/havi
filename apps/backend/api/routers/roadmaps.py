"""Router cho Roadmap Engine, Tasks, Evidence & Reviews (Havi 3.0)."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.deps import AuthDep, RoadmapServiceDep, WorkspaceDep
from core.enums import ReviewDecision

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


# --- Schemas ---
class GenerateRoadmapRequest(BaseModel):
    goal_id: UUID = Field(..., description="ID mục tiêu cần sinh lộ trình")


class CompleteTaskRequest(BaseModel):
    evidence_text: str = Field(
        ..., min_length=1, description="Nội dung kết quả / bằng chứng thực tế"
    )
    evidence_type: str = Field(
        default="note", description="Loại bằng chứng (note, image, link, transfer, metric)"
    )
    value_number: float | None = Field(default=None, description="Số liệu đo lường cụ thể (nếu có)")
    media_asset_id: UUID | None = Field(default=None, description="Ảnh hoặc video bằng chứng")


class BlockTaskRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Lý do bị kẹt")
    use_fallback: bool = Field(default=False, description="Chuyển sang phương án dự phòng nhỏ hơn")


class ReviewRoadmapRequest(BaseModel):
    completed_summary: str = Field(..., description="Tóm tắt những gì đã làm được")
    evidence_summary: str = Field(..., description="Tóm tắt kết quả / bằng chứng đạt được")
    obstacles_summary: str = Field(..., description="Tóm tắt khó khăn / rào cản")
    decision: ReviewDecision = Field(
        default=ReviewDecision.CONTINUE, description="Quyết định tiếp theo"
    )
    replan_diff: dict | None = Field(default=None, description="Đề xuất điều chỉnh lộ trình")


class TaskResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    roadmap_id: UUID
    goal_id: UUID
    title: str
    description: str | None
    why_this_is_next: str
    time_estimate_minutes: int
    owner_type: str
    capability_module: str
    inputs_needed: str | None
    done_rule: str
    fallback_action: str | None
    status: str
    scheduled_date: datetime | None
    completed_at: datetime | None
    evidence_notes: str | None
    order_index: int
    created_at: datetime


class RoadmapResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    goal_id: UUID
    version: int
    title: str
    horizon_90d: str
    horizon_30d: str
    horizon_7d: str
    assumptions: list[str] | None
    confidence_score: float
    status: str
    created_at: datetime


class ActiveRoadmapResponse(BaseModel):
    roadmap: RoadmapResponse
    tasks: list[TaskResponse]


class EvidenceResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    goal_id: UUID
    task_id: UUID | None
    source: str
    evidence_type: str
    value_number: float | None
    value_text: str
    media_asset_id: UUID | None
    confidence: float
    created_at: datetime


class ReviewResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    goal_id: UUID
    roadmap_id: UUID
    review_date: datetime
    completed_summary: str
    evidence_summary: str
    obstacles_summary: str
    decision: str
    replan_diff: dict | None
    user_accepted: bool


# --- Endpoints ---
@router.post("/generate", response_model=ActiveRoadmapResponse, status_code=status.HTTP_201_CREATED)
async def generate_roadmap(
    data: GenerateRoadmapRequest,
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: RoadmapServiceDep,
) -> ActiveRoadmapResponse:
    try:
        roadmap, tasks = await service.generate_roadmap_for_goal(
            workspace_id=workspace_id,
            goal_id=data.goal_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ActiveRoadmapResponse(
        roadmap=RoadmapResponse(
            id=roadmap.id,
            workspace_id=roadmap.workspace_id,
            goal_id=roadmap.goal_id,
            version=roadmap.version,
            title=roadmap.title,
            horizon_90d=roadmap.horizon_90d,
            horizon_30d=roadmap.horizon_30d,
            horizon_7d=roadmap.horizon_7d,
            assumptions=roadmap.assumptions,
            confidence_score=roadmap.confidence_score,
            status=roadmap.status,
            created_at=roadmap.created_at,
        ),
        tasks=[
            TaskResponse(
                id=t.id,
                workspace_id=t.workspace_id,
                roadmap_id=t.roadmap_id,
                goal_id=t.goal_id,
                title=t.title,
                description=t.description,
                why_this_is_next=t.why_this_is_next,
                time_estimate_minutes=t.time_estimate_minutes,
                owner_type=t.owner_type,
                capability_module=t.capability_module,
                inputs_needed=t.inputs_needed,
                done_rule=t.done_rule,
                fallback_action=t.fallback_action,
                status=t.status,
                scheduled_date=t.scheduled_date,
                completed_at=t.completed_at,
                evidence_notes=t.evidence_notes,
                order_index=t.order_index,
                created_at=t.created_at,
            )
            for t in tasks
        ],
    )


@router.get("/active", response_model=ActiveRoadmapResponse | None)
async def get_active_roadmap(
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: RoadmapServiceDep,
) -> ActiveRoadmapResponse | None:
    roadmap, tasks = await service.get_active_roadmap(workspace_id=workspace_id)
    if not roadmap:
        return None

    return ActiveRoadmapResponse(
        roadmap=RoadmapResponse(
            id=roadmap.id,
            workspace_id=roadmap.workspace_id,
            goal_id=roadmap.goal_id,
            version=roadmap.version,
            title=roadmap.title,
            horizon_90d=roadmap.horizon_90d,
            horizon_30d=roadmap.horizon_30d,
            horizon_7d=roadmap.horizon_7d,
            assumptions=roadmap.assumptions,
            confidence_score=roadmap.confidence_score,
            status=roadmap.status,
            created_at=roadmap.created_at,
        ),
        tasks=[
            TaskResponse(
                id=t.id,
                workspace_id=t.workspace_id,
                roadmap_id=t.roadmap_id,
                goal_id=t.goal_id,
                title=t.title,
                description=t.description,
                why_this_is_next=t.why_this_is_next,
                time_estimate_minutes=t.time_estimate_minutes,
                owner_type=t.owner_type,
                capability_module=t.capability_module,
                inputs_needed=t.inputs_needed,
                done_rule=t.done_rule,
                fallback_action=t.fallback_action,
                status=t.status,
                scheduled_date=t.scheduled_date,
                completed_at=t.completed_at,
                evidence_notes=t.evidence_notes,
                order_index=t.order_index,
                created_at=t.created_at,
            )
            for t in tasks
        ],
    )


@router.get("/today", response_model=TaskResponse | None)
async def get_today_action(
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: RoadmapServiceDep,
) -> TaskResponse | None:
    task = await service.get_today_action(workspace_id=workspace_id)
    if not task:
        return None
    return TaskResponse(
        id=task.id,
        workspace_id=task.workspace_id,
        roadmap_id=task.roadmap_id,
        goal_id=task.goal_id,
        title=task.title,
        description=task.description,
        why_this_is_next=task.why_this_is_next,
        time_estimate_minutes=task.time_estimate_minutes,
        owner_type=task.owner_type,
        capability_module=task.capability_module,
        inputs_needed=task.inputs_needed,
        done_rule=task.done_rule,
        fallback_action=task.fallback_action,
        status=task.status,
        scheduled_date=task.scheduled_date,
        completed_at=task.completed_at,
        evidence_notes=task.evidence_notes,
        order_index=task.order_index,
        created_at=task.created_at,
    )


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: UUID,
    data: CompleteTaskRequest,
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: RoadmapServiceDep,
) -> TaskResponse:
    try:
        updated_task, _ = await service.complete_task_with_evidence(
            workspace_id=workspace_id,
            task_id=task_id,
            evidence_text=data.evidence_text,
            evidence_type=data.evidence_type,
            value_number=data.value_number,
            media_asset_id=data.media_asset_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TaskResponse(
        id=updated_task.id,
        workspace_id=updated_task.workspace_id,
        roadmap_id=updated_task.roadmap_id,
        goal_id=updated_task.goal_id,
        title=updated_task.title,
        description=updated_task.description,
        why_this_is_next=updated_task.why_this_is_next,
        time_estimate_minutes=updated_task.time_estimate_minutes,
        owner_type=updated_task.owner_type,
        capability_module=updated_task.capability_module,
        inputs_needed=updated_task.inputs_needed,
        done_rule=updated_task.done_rule,
        fallback_action=updated_task.fallback_action,
        status=updated_task.status,
        scheduled_date=updated_task.scheduled_date,
        completed_at=updated_task.completed_at,
        evidence_notes=updated_task.evidence_notes,
        order_index=updated_task.order_index,
        created_at=updated_task.created_at,
    )


@router.post("/tasks/{task_id}/block", response_model=TaskResponse)
async def block_task(
    task_id: UUID,
    data: BlockTaskRequest,
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: RoadmapServiceDep,
) -> TaskResponse:
    try:
        updated_task = await service.block_task(
            workspace_id=workspace_id,
            task_id=task_id,
            reason=data.reason,
            use_fallback=data.use_fallback,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TaskResponse(
        id=updated_task.id,
        workspace_id=updated_task.workspace_id,
        roadmap_id=updated_task.roadmap_id,
        goal_id=updated_task.goal_id,
        title=updated_task.title,
        description=updated_task.description,
        why_this_is_next=updated_task.why_this_is_next,
        time_estimate_minutes=updated_task.time_estimate_minutes,
        owner_type=updated_task.owner_type,
        capability_module=updated_task.capability_module,
        inputs_needed=updated_task.inputs_needed,
        done_rule=updated_task.done_rule,
        fallback_action=updated_task.fallback_action,
        status=updated_task.status,
        scheduled_date=updated_task.scheduled_date,
        completed_at=updated_task.completed_at,
        evidence_notes=updated_task.evidence_notes,
        order_index=updated_task.order_index,
        created_at=updated_task.created_at,
    )


@router.post("/tasks/{task_id}/reopen", response_model=TaskResponse)
async def reopen_task(
    task_id: UUID,
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: RoadmapServiceDep,
) -> TaskResponse:
    try:
        updated_task = await service.reopen_task(
            workspace_id=workspace_id,
            task_id=task_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TaskResponse(
        id=updated_task.id,
        workspace_id=updated_task.workspace_id,
        roadmap_id=updated_task.roadmap_id,
        goal_id=updated_task.goal_id,
        title=updated_task.title,
        description=updated_task.description,
        why_this_is_next=updated_task.why_this_is_next,
        time_estimate_minutes=updated_task.time_estimate_minutes,
        owner_type=updated_task.owner_type,
        capability_module=updated_task.capability_module,
        inputs_needed=updated_task.inputs_needed,
        done_rule=updated_task.done_rule,
        fallback_action=updated_task.fallback_action,
        status=updated_task.status,
        scheduled_date=updated_task.scheduled_date,
        completed_at=updated_task.completed_at,
        evidence_notes=updated_task.evidence_notes,
        order_index=updated_task.order_index,
        created_at=updated_task.created_at,
    )


@router.post("/{roadmap_id}/review", response_model=ReviewResponse)
async def create_review(
    roadmap_id: UUID,
    data: ReviewRoadmapRequest,
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: RoadmapServiceDep,
) -> ReviewResponse:
    try:
        review = await service.create_weekly_review(
            workspace_id=workspace_id,
            roadmap_id=roadmap_id,
            completed_summary=data.completed_summary,
            evidence_summary=data.evidence_summary,
            obstacles_summary=data.obstacles_summary,
            decision=data.decision.value,
            replan_diff=data.replan_diff,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ReviewResponse(
        id=review.id,
        workspace_id=review.workspace_id,
        goal_id=review.goal_id,
        roadmap_id=review.roadmap_id,
        review_date=review.review_date,
        completed_summary=review.completed_summary,
        evidence_summary=review.evidence_summary,
        obstacles_summary=review.obstacles_summary,
        decision=review.decision,
        replan_diff=review.replan_diff,
        user_accepted=review.user_accepted,
    )


@router.get("/history", response_model=list[RoadmapResponse])
async def list_roadmap_history(
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: RoadmapServiceDep,
) -> list[RoadmapResponse]:
    history = await service.list_roadmap_history(workspace_id=workspace_id)
    return [
        RoadmapResponse(
            id=r.id,
            workspace_id=r.workspace_id,
            goal_id=r.goal_id,
            version=r.version,
            title=r.title,
            horizon_90d=r.horizon_90d,
            horizon_30d=r.horizon_30d,
            horizon_7d=r.horizon_7d,
            assumptions=r.assumptions,
            confidence_score=r.confidence_score,
            status=r.status,
            created_at=r.created_at,
        )
        for r in history
    ]


@router.post("/{roadmap_id}/restore", response_model=ActiveRoadmapResponse)
async def restore_roadmap(
    roadmap_id: UUID,
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: RoadmapServiceDep,
) -> ActiveRoadmapResponse:
    try:
        roadmap, tasks = await service.restore_roadmap_version(
            workspace_id=workspace_id,
            roadmap_id=roadmap_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ActiveRoadmapResponse(
        roadmap=RoadmapResponse(
            id=roadmap.id,
            workspace_id=roadmap.workspace_id,
            goal_id=roadmap.goal_id,
            version=roadmap.version,
            title=roadmap.title,
            horizon_90d=roadmap.horizon_90d,
            horizon_30d=roadmap.horizon_30d,
            horizon_7d=roadmap.horizon_7d,
            assumptions=roadmap.assumptions,
            confidence_score=roadmap.confidence_score,
            status=roadmap.status,
            created_at=roadmap.created_at,
        ),
        tasks=[
            TaskResponse(
                id=t.id,
                workspace_id=t.workspace_id,
                roadmap_id=t.roadmap_id,
                goal_id=t.goal_id,
                title=t.title,
                description=t.description,
                why_this_is_next=t.why_this_is_next,
                time_estimate_minutes=t.time_estimate_minutes,
                owner_type=t.owner_type,
                capability_module=t.capability_module,
                inputs_needed=t.inputs_needed,
                done_rule=t.done_rule,
                fallback_action=t.fallback_action,
                status=t.status,
                scheduled_date=t.scheduled_date,
                completed_at=t.completed_at,
                evidence_notes=t.evidence_notes,
                order_index=t.order_index,
                created_at=t.created_at,
            )
            for t in tasks
        ],
    )


@router.get("/evidence", response_model=list[EvidenceResponse])
async def list_evidence(
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: RoadmapServiceDep,
) -> list[EvidenceResponse]:
    evidence_list = await service.list_evidence(workspace_id=workspace_id)
    return [
        EvidenceResponse(
            id=e.id,
            workspace_id=e.workspace_id,
            goal_id=e.goal_id,
            task_id=e.task_id,
            source=e.source,
            evidence_type=e.evidence_type,
            value_number=e.value_number,
            value_text=e.value_text,
            media_asset_id=e.media_asset_id,
            confidence=e.confidence,
            created_at=e.created_at,
        )
        for e in evidence_list
    ]


@router.get("/reviews", response_model=list[ReviewResponse])
async def list_reviews(
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: RoadmapServiceDep,
) -> list[ReviewResponse]:
    reviews = await service.list_reviews(workspace_id=workspace_id)
    return [
        ReviewResponse(
            id=rv.id,
            workspace_id=rv.workspace_id,
            goal_id=rv.goal_id,
            roadmap_id=rv.roadmap_id,
            review_date=rv.review_date,
            completed_summary=rv.completed_summary,
            evidence_summary=rv.evidence_summary,
            obstacles_summary=rv.obstacles_summary,
            decision=rv.decision,
            replan_diff=rv.replan_diff,
            user_accepted=rv.user_accepted,
        )
        for rv in reviews
    ]
