"""Tests cho GoalService & GoalRepository (Havi 3.0)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.goal_repository import GoalRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.goal_service import GoalService
from core.enums import GoalCategory, GoalStatus, Industry


@pytest.mark.asyncio
async def test_create_and_get_active_goal(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        email=f"goal_test_{uuid.uuid4().hex[:6]}@havi.vn",
        name="Thầy Minh",
        password_hash="test_hash",
    )
    ws_repo = WorkspaceRepository(db_session)
    ws = await ws_repo.create(
        name="Trung Tâm Nhật Minh", industry=Industry.EDUCATION, owner_user_id=user.id
    )
    ws_id = ws.id

    goal_repo = GoalRepository(db_session)
    goal_service = GoalService(goal_repo=goal_repo)

    # Tạo goal
    goal = await goal_service.create_goal(
        workspace_id=ws_id,
        title="Tuyển sinh 20 học viên khóa Lập trình AI",
        category=GoalCategory.ACQUIRE_CUSTOMERS.value,
        evidence_definition="Học viên xác nhận đóng học phí qua VietQR",
        description="Mục tiêu tháng này cho Trung Tâm Công Nghệ Nhật Minh",
        weekly_capacity_hours=12,
    )

    assert goal.id is not None
    assert goal.workspace_id == ws_id
    assert goal.title == "Tuyển sinh 20 học viên khóa Lập trình AI"
    assert goal.status == GoalStatus.ACTIVE.value
    assert goal.weekly_capacity_hours == 12

    # Lấy active goal
    active = await goal_service.get_active_goal(workspace_id=ws_id)
    assert active is not None
    assert active.id == goal.id

    # Danh sách goals
    goals = await goal_service.list_goals(workspace_id=ws_id)
    assert len(goals) == 1
    assert goals[0].id == goal.id


@pytest.mark.asyncio
async def test_tenant_isolation_for_goals(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    user_a = await user_repo.create(
        email=f"user_a_{uuid.uuid4().hex[:6]}@havi.vn",
        name="Chủ A",
        password_hash="test_hash",
    )
    user_b = await user_repo.create(
        email=f"user_b_{uuid.uuid4().hex[:6]}@havi.vn",
        name="Chủ B",
        password_hash="test_hash",
    )
    ws_repo = WorkspaceRepository(db_session)
    ws_a = (await ws_repo.create(name="Tiệm A", industry=Industry.SPA, owner_user_id=user_a.id)).id
    ws_b = (await ws_repo.create(name="Tiệm B", industry=Industry.SPA, owner_user_id=user_b.id)).id

    goal_repo = GoalRepository(db_session)
    goal_service = GoalService(goal_repo=goal_repo)

    goal_a = await goal_service.create_goal(
        workspace_id=ws_a,
        title="Goal Workspace A",
        category=GoalCategory.LAUNCH.value,
        evidence_definition="Ra mắt sản phẩm A",
    )

    # Workspace B không thấy goal của Workspace A
    active_b = await goal_service.get_active_goal(workspace_id=ws_b)
    assert active_b is None

    goals_b = await goal_service.list_goals(workspace_id=ws_b)
    assert len(goals_b) == 0

    # Get by ID sai workspace trả về None
    not_found = await goal_service.get_goal(workspace_id=ws_b, goal_id=goal_a.id)
    assert not_found is None
