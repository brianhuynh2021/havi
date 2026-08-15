"""Test suite cho CrmNudgeService."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.crm_nudge_repository import CrmNudgeRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.lead_repository import LeadRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.crm_nudge_service import CrmNudgeService
from core.enums import CrmMessageStatus, Industry, LeadSource, LeadStage
from domain.models.lead import Lead
from domain.models.user import User
from domain.models.workspace import Workspace


@pytest.mark.asyncio
async def test_crm_nudge_service_scan_and_approve(db_session: AsyncSession):
    session = db_session
    ws_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    user = User(id=owner_id, email=f"owner_{ws_id}@havi.vn", password_hash="pw", name="Owner")
    session.add(user)
    await session.flush()
    ws = Workspace(id=ws_id, name="Spa Sen Vàng", industry=Industry.SPA, owner_user_id=owner_id)
    session.add(ws)
    await session.flush()

    # Lead cũ 45 ngày trước
    old_date = datetime.now(UTC) - timedelta(days=45)
    lead_old = Lead(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        name="Chị Lan",
        phone="0901234567",
        source=LeadSource.FANPAGE,
        stage=LeadStage.WON,
    )
    session.add(lead_old)
    await session.flush()
    lead_old.created_at = old_date
    await session.flush()

    # Lead mới 5 ngày trước
    lead_new = Lead(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        name="Anh Nam",
        phone="0907654321",
        source=LeadSource.CRM,
        stage=LeadStage.NEW,
    )
    session.add(lead_new)
    await session.flush()

    service = CrmNudgeService(
        nudge_repo=CrmNudgeRepository(session),
        workspace_repo=WorkspaceRepository(session),
        profile_repo=BrandProfileRepository(session),
        event_repo=EventLogRepository(session),
    )

    # 1. Scan nudges
    created = await service.scan_and_generate_nudges(workspace_id=ws_id, inactive_days=30)
    assert len(created) == 1
    assert created[0].lead_id == lead_old.id
    assert created[0].status == CrmMessageStatus.PENDING_APPROVAL
    assert "Chị Lan" in created[0].message
    assert "Spa Sen Vàng" in created[0].message

    # Scan lại ngay sau đó -> Không sinh trùng
    created_again = await service.scan_and_generate_nudges(workspace_id=ws_id, inactive_days=30)
    assert len(created_again) == 0

    # 2. List nudges
    items, total = await service.list_nudges(workspace_id=ws_id)
    assert total == 1
    assert items[0].id == created[0].id

    # 3. Approve and send
    approved = await service.approve_and_send(workspace_id=ws_id, nudge_id=created[0].id)
    assert approved.status == CrmMessageStatus.SENT
    assert approved.sent_at is not None

    # 4. Dismiss test
    nudge_dismiss_test = await CrmNudgeRepository(session).create(
        workspace_id=ws_id,
        lead_id=lead_new.id,
        message="Tin test",
    )
    dismissed = await service.dismiss(workspace_id=ws_id, nudge_id=nudge_dismiss_test.id)
    assert dismissed.status == CrmMessageStatus.DISMISSED
