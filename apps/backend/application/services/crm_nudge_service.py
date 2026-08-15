"""Application Service cho CRM Lifecycle Nudges (Chăm sóc khách cũ tự động)."""

from uuid import UUID

from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.crm_nudge_repository import CrmNudgeRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from core.enums import CrmMessageStatus, CrmNudgeType, Industry
from domain.models.crm_nudge import CrmNudge
from domain.policies.nudge_policy import generate_nudge_message


class CrmNudgeNotFound(Exception):
    pass


class CrmNudgeService:
    def __init__(
        self,
        *,
        nudge_repo: CrmNudgeRepository,
        workspace_repo: WorkspaceRepository,
        profile_repo: BrandProfileRepository,
        event_repo: EventLogRepository,
    ) -> None:
        self._nudges = nudge_repo
        self._workspaces = workspace_repo
        self._profiles = profile_repo
        self._events = event_repo

    async def scan_and_generate_nudges(
        self, *, workspace_id: UUID, inactive_days: int = 30
    ) -> list[CrmNudge]:
        """Quét khách hàng quá `inactive_days` ngày chưa quay lại và tạo bản ghi nudge dự thảo."""
        ws = await self._workspaces.get(workspace_id)
        if not ws:
            return []

        industry = ws.industry or Industry.OTHER
        brand_name = ws.name

        inactive_leads = await self._nudges.list_inactive_leads(
            workspace_id=workspace_id, inactive_days=inactive_days
        )

        created_nudges: list[CrmNudge] = []
        for lead in inactive_leads:
            has_recent = await self._nudges.has_recent_nudge_for_lead(
                lead_id=lead.id, within_days=inactive_days
            )
            if has_recent:
                continue

            msg = generate_nudge_message(
                lead_name=lead.name,
                industry=industry,
                nudge_type=CrmNudgeType.INACTIVE_30_DAYS,
                brand_name=brand_name,
                discount_percent=20,
            )

            nudge = await self._nudges.create(
                workspace_id=workspace_id,
                lead_id=lead.id,
                message=msg,
                nudge_type=CrmNudgeType.INACTIVE_30_DAYS,
            )
            created_nudges.append(nudge)

        return created_nudges

    async def list_nudges(
        self,
        *,
        workspace_id: UUID,
        status: CrmMessageStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[CrmNudge], int]:
        return await self._nudges.list_by_workspace(
            workspace_id=workspace_id, status=status, limit=limit, offset=offset
        )

    async def approve_and_send(self, *, workspace_id: UUID, nudge_id: UUID) -> CrmNudge:
        nudge = await self._nudges.mark_sent(workspace_id=workspace_id, nudge_id=nudge_id)
        if not nudge:
            raise CrmNudgeNotFound("Tin nhắc chăm sóc khách hàng không tồn tại")
        return nudge

    async def dismiss(self, *, workspace_id: UUID, nudge_id: UUID) -> CrmNudge:
        nudge = await self._nudges.mark_dismissed(workspace_id=workspace_id, nudge_id=nudge_id)
        if not nudge:
            raise CrmNudgeNotFound("Tin nhắc chăm sóc khách hàng không tồn tại")
        return nudge
