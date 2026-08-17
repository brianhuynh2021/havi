"""AI Lead Agent Service — tự động phân tích tin nhắn, trích xuất SĐT/Zalo và tạo hồ sơ CRM."""

import logging
from uuid import UUID

from adapters.persistence.inbox_repository import InboxRepository
from adapters.persistence.lead_repository import LeadRepository
from core.enums import LeadReplyStatus, LeadSource, LeadStage
from domain.models.lead import Lead
from domain.policies.ai_lead_intent import LeadAnalysisResult, classify_lead_intent

logger = logging.getLogger("havi.ai_lead_agent_service")


class AILeadAgentService:
    def __init__(
        self,
        *,
        leads: LeadRepository,
        inbox: InboxRepository | None = None,
    ) -> None:
        self._leads = leads
        self._inbox = inbox

    async def process_incoming_lead_message(
        self,
        *,
        workspace_id: UUID,
        author_name: str,
        message: str,
        source: LeadSource = LeadSource.FANPAGE,
    ) -> tuple[Lead, LeadAnalysisResult]:
        """Tiếp nhận tin nhắn mới từ khách/học viên: phân tích intent, trích xuất SĐT và lưu Lead vào CRM."""
        analysis = classify_lead_intent(message, author_name=author_name)

        stage = LeadStage.NEW
        if analysis.extracted_phone:
            stage = LeadStage.QUALIFIED  # Có số điện thoại là Lead tiềm năng đã xác thực (QUALIFIED)

        # Ghi chú chi tiết từ phân tích AI
        notes = f"[AI Intent: {analysis.intent.value} (conf={analysis.confidence:.2f})] Tags: {', '.join(analysis.suggested_tags)}"

        lead = await self._leads.create(
            workspace_id=workspace_id,
            name=author_name or "Khách hàng mới",
            phone=analysis.extracted_phone,
            source=source,
            stage=stage,
            reply_status=LeadReplyStatus.AWAITING_APPROVAL,
            message=message,
            suggested_reply=analysis.suggested_reply,
            notes=notes,
        )

        logger.info(
            "AI Lead Agent provisioned lead id=%s for workspace=%s with intent=%s phone=%s",
            lead.id,
            workspace_id,
            analysis.intent.value,
            analysis.extracted_phone,
        )

        return lead, analysis
