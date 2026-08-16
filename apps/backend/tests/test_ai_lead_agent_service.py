"""Unit tests for AILeadAgentService and Intent Policies (Milestone #9)."""

import pytest
from uuid import uuid4

from application.services.ai_lead_agent_service import AILeadAgentService
from domain.policies.ai_lead_intent import (
    classify_lead_intent,
    extract_vietnam_phone,
    LeadIntentKind,
)
from core.enums import LeadStage


def test_extract_vietnam_phone():
    assert extract_vietnam_phone("Em xin giá sđt 0901234567 nhé") == "0901234567"
    assert extract_vietnam_phone("Zalo +84 988 123 456") == "0988123456"
    assert extract_vietnam_phone("Số của mình: 035.888.9999 tư vấn giúp") == "0358889999"
    assert extract_vietnam_phone("Không có số điện thoại nào ở đây") is None


def test_classify_lead_intent_price():
    res = classify_lead_intent("Khóa học sửa chữa điện tử học phí bao nhiêu vậy shop?", author_name="Tuấn Anh")
    assert res.intent == LeadIntentKind.PRICE_INQUIRY
    assert res.confidence >= 0.9
    assert "#hoi_hoc_phi" in res.suggested_tags
    assert "Nhật Minh" in res.suggested_reply
    assert "Tuấn Anh" in res.suggested_reply


def test_classify_lead_intent_enrollment_with_phone():
    res = classify_lead_intent("Mình muốn đăng ký học lớp cấp tốc, sđt 0912345678", author_name="Minh")
    assert res.intent == LeadIntentKind.ENROLLMENT
    assert res.extracted_phone == "0912345678"
    assert "#co_so_dien_thoai" in res.suggested_tags
    assert "#hot_lead" in res.suggested_tags


@pytest.mark.asyncio
async def test_ai_lead_agent_service_provisions_warm_lead_on_phone():
    # Mock LeadRepository
    class FakeLeadRepo:
        def __init__(self):
            self.created_leads = []

        async def create(self, **kwargs):
            from domain.models.lead import Lead
            lead = Lead(id=uuid4(), **kwargs)
            self.created_leads.append(lead)
            return lead

    fake_repo = FakeLeadRepo()
    service = AILeadAgentService(leads=fake_repo)

    ws_id = uuid4()
    lead, analysis = await service.process_incoming_lead_message(
        workspace_id=ws_id,
        author_name="Học viên Tuấn",
        message="Cho mình hỏi học phí khóa thực hành và lịch học nhé, số Zalo mình 0977112233",
    )

    assert lead.phone == "0977112233"
    assert lead.stage == LeadStage.QUALIFIED
    assert lead.name == "Học viên Tuấn"
    assert analysis.intent == LeadIntentKind.PRICE_INQUIRY
