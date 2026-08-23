"""Tests cho RoadmapService & RoadmapRepository (Havi 3.0)."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.goal_repository import GoalRepository
from adapters.persistence.roadmap_repository import RoadmapRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.goal_service import GoalService
from application.services.roadmap_service import RoadmapService
from core.enums import GoalCategory, Industry, ReviewDecision, TaskStatus


@pytest.mark.asyncio
async def test_roadmap_lifecycle_and_task_execution(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        email=f"roadmap_test_{uuid.uuid4().hex[:6]}@havi.vn",
        name="Chị Hương",
        password_hash="test_hash",
    )
    ws_repo = WorkspaceRepository(db_session)
    ws = await ws_repo.create(name="Spa An Nhiên", industry=Industry.SPA, owner_user_id=user.id)
    ws_id = ws.id


    goal_repo = GoalRepository(db_session)

    roadmap_repo = RoadmapRepository(db_session)
    event_repo = EventLogRepository(db_session)

    goal_service = GoalService(goal_repo=goal_repo)
    roadmap_service = RoadmapService(
        roadmap_repo=roadmap_repo,
        goal_repo=goal_repo,
        event_repo=event_repo,
    )


    # 1. Tạo mục tiêu
    goal = await goal_service.create_goal(
        workspace_id=ws_id,
        title="Thu hút 50 khách trải nghiệm dịch vụ Spa",
        category=GoalCategory.ACQUIRE_CUSTOMERS.value,
        evidence_definition="Mã QR voucher được quét tại tiệm",
    )

    # 2. Sinh lộ trình tự động
    roadmap, tasks = await roadmap_service.generate_roadmap_for_goal(
        workspace_id=ws_id,
        goal_id=goal.id,
    )

    assert roadmap.id is not None
    assert roadmap.version == 1
    assert "90" in roadmap.horizon_90d or len(roadmap.horizon_90d) > 0
    assert len(tasks) >= 3

    # 3. Lấy hành động đề xuất hôm nay (Next Recommended Action)
    today_action = await roadmap_service.get_today_action(workspace_id=ws_id)
    assert today_action is not None
    assert today_action.id == tasks[0].id
    assert today_action.status == TaskStatus.PENDING.value
    assert len(today_action.why_this_is_next) > 0
    assert len(today_action.done_rule) > 0

    # 4. Hoàn thành nhiệm vụ kèm bằng chứng (Evidence)
    updated_task, evidence = await roadmap_service.complete_task_with_evidence(
        workspace_id=ws_id,
        task_id=today_action.id,
        evidence_text="Đã hoàn thiện bài viết ưu đãi giảm 30% và đăng thử nghiệm",
        evidence_type="note",
    )

    assert updated_task.status == TaskStatus.COMPLETED.value
    assert updated_task.completed_at is not None
    assert evidence.id is not None
    assert evidence.value_text == "Đã hoàn thiện bài viết ưu đãi giảm 30% và đăng thử nghiệm"

    # 5. Kiểm tra hành động tiếp theo sau khi task 1 hoàn thành
    next_action = await roadmap_service.get_today_action(workspace_id=ws_id)
    assert next_action is not None
    assert next_action.id == tasks[1].id

    # 6. Test xử lý khi bị kẹt (Block task with fallback)
    blocked_task = await roadmap_service.block_task(
        workspace_id=ws_id,
        task_id=next_action.id,
        reason="Chưa quay được video vì trời mưa",
        use_fallback=True,
    )
    assert blocked_task.id == next_action.id

    # 7. Đánh giá hàng tuần (Weekly Review)
    review = await roadmap_service.create_weekly_review(
        workspace_id=ws_id,
        roadmap_id=roadmap.id,
        completed_summary="Đã hoàn thành bài viết ưu đãi",
        evidence_summary="Có 5 lượt quan tâm trên Fanpage",
        obstacles_summary="Cần thêm hình ảnh thực tế",
        decision=ReviewDecision.CONTINUE.value,
    )
    assert review.id is not None
    assert review.decision == ReviewDecision.CONTINUE.value
    assert review.user_accepted is True
