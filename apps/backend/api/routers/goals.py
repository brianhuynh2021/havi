"""Router cho Goal Management (Havi 3.0)."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.deps import AuthDep, GoalServiceDep, WorkspaceDep
from core.enums import GoalCategory, GoalStatus

router = APIRouter(prefix="/goals", tags=["goals"])


class CreateGoalRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Tiêu đề mục tiêu")
    category: GoalCategory = Field(
        default=GoalCategory.ACQUIRE_CUSTOMERS, description="Nhóm mục tiêu"
    )
    evidence_definition: str = Field(
        ..., min_length=1, description="Định nghĩa bằng chứng hoàn thành"
    )
    description: str | None = Field(default=None, description="Mô tả chi tiết")
    target_deadline: datetime | None = Field(default=None, description="Hạn chót mục tiêu")
    weekly_capacity_hours: int = Field(default=10, ge=1, le=100, description="Số giờ cam kết/tuần")
    constraints: dict | None = Field(default=None, description="Ràng buộc hoặc tài nguyên")


class UpdateGoalRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: GoalStatus | None = None
    evidence_definition: str | None = None
    target_deadline: datetime | None = None
    weekly_capacity_hours: int | None = None
    constraints: dict | None = None


class GoalResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    description: str | None
    category: str
    evidence_definition: str
    target_deadline: datetime | None
    weekly_capacity_hours: int
    constraints: dict | None
    status: str
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    data: CreateGoalRequest,
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: GoalServiceDep,
) -> GoalResponse:
    goal = await service.create_goal(
        workspace_id=workspace_id,
        title=data.title,
        category=data.category.value,
        evidence_definition=data.evidence_definition,
        description=data.description,
        target_deadline=data.target_deadline,
        weekly_capacity_hours=data.weekly_capacity_hours,
        constraints=data.constraints,
    )
    return GoalResponse(
        id=goal.id,
        workspace_id=goal.workspace_id,
        title=goal.title,
        description=goal.description,
        category=goal.category,
        evidence_definition=goal.evidence_definition,
        target_deadline=goal.target_deadline,
        weekly_capacity_hours=goal.weekly_capacity_hours,
        constraints=goal.constraints,
        status=goal.status,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


@router.get("/active", response_model=GoalResponse | None)
async def get_active_goal(
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: GoalServiceDep,
) -> GoalResponse | None:
    goal = await service.get_active_goal(workspace_id=workspace_id)
    if not goal:
        return None
    return GoalResponse(
        id=goal.id,
        workspace_id=goal.workspace_id,
        title=goal.title,
        description=goal.description,
        category=goal.category,
        evidence_definition=goal.evidence_definition,
        target_deadline=goal.target_deadline,
        weekly_capacity_hours=goal.weekly_capacity_hours,
        constraints=goal.constraints,
        status=goal.status,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


@router.get("", response_model=list[GoalResponse])
async def list_goals(
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: GoalServiceDep,
) -> list[GoalResponse]:
    goals = await service.list_goals(workspace_id=workspace_id)
    return [
        GoalResponse(
            id=g.id,
            workspace_id=g.workspace_id,
            title=g.title,
            description=g.description,
            category=g.category,
            evidence_definition=g.evidence_definition,
            target_deadline=g.target_deadline,
            weekly_capacity_hours=g.weekly_capacity_hours,
            constraints=g.constraints,
            status=g.status,
            created_at=g.created_at,
            updated_at=g.updated_at,
        )
        for g in goals
    ]


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: UUID,
    data: UpdateGoalRequest,
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: GoalServiceDep,
) -> GoalResponse:
    goal = await service.update_goal(
        workspace_id=workspace_id,
        goal_id=goal_id,
        title=data.title,
        description=data.description,
        status=data.status.value if data.status else None,
        evidence_definition=data.evidence_definition,
        target_deadline=data.target_deadline,
        weekly_capacity_hours=data.weekly_capacity_hours,
        constraints=data.constraints,
    )
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục tiêu")
    return GoalResponse(
        id=goal.id,
        workspace_id=goal.workspace_id,
        title=goal.title,
        description=goal.description,
        category=goal.category,
        evidence_definition=goal.evidence_definition,
        target_deadline=goal.target_deadline,
        weekly_capacity_hours=goal.weekly_capacity_hours,
        constraints=goal.constraints,
        status=goal.status,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_or_reset_goal(
    goal_id: UUID,
    workspace_id: WorkspaceDep,
    _auth: AuthDep,
    service: GoalServiceDep,
) -> None:
    success = await service.archive_goal(workspace_id=workspace_id, goal_id=goal_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục tiêu")
