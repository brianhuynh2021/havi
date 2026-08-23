"""Router cho Campaign Simulation & Ads Readiness (Havi Phase 5)."""

from fastapi import APIRouter

from api.deps import AuthDep, WorkspaceDep
from application.services.campaign_simulator import (
    CampaignSimulationInput,
    CampaignSimulationResult,
    CampaignSimulator,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
_simulator = CampaignSimulator()


@router.post("/simulate", response_model=CampaignSimulationResult)
async def simulate_campaign(
    data: CampaignSimulationInput,
    _ws: WorkspaceDep,
    _auth: AuthDep,
) -> CampaignSimulationResult:
    """Mô phỏng phạm vi tiếp cận và hội thoại ước tính trước khi tạo chiến dịch."""
    return _simulator.simulate(data)
