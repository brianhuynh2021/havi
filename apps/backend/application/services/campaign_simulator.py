"""Campaign Brief & Simulation Engine (Havi Phase 5).

Provides deterministic reach & lead simulation for local marketing campaigns (Facebook/Meta)
without launching live spend. Enforces transparent disclaimers and safety guardrails.
"""

from pydantic import BaseModel, Field


class CampaignSimulationInput(BaseModel):
    objective: str = Field(default="messages", description="Mục tiêu chiến dịch: messages, reach, leads, store_visits")
    radius_km: float = Field(default=5.0, ge=1.0, le=50.0, description="Bán kính địa phương (km)")
    daily_budget_vnd: float = Field(default=100000.0, ge=50000.0, le=2000000.0, description="Ngân sách ngày (VNĐ)")
    duration_days: int = Field(default=7, ge=1, le=30, description="Số ngày chạy chiến dịch")
    target_audience: str = Field(default="Khách hàng địa phương quan tâm dịch vụ", description="Mô tả tệp khách hàng")


class CampaignSimulationResult(BaseModel):
    objective: str
    radius_km: float
    daily_budget_vnd: float
    duration_days: int
    total_budget_vnd: float
    estimated_reach_min: int
    estimated_reach_max: int
    estimated_conversations_min: int
    estimated_conversations_max: int
    estimated_cpm_vnd: float
    disclaimer: str
    safety_guardrails: list[str]


class CampaignSimulator:
    """Mô phỏng hiệu quả chiến dịch dựa trên benchmark thực tế tại Việt Nam."""

    # Benchmark CPM tại Việt Nam: ~25.000đ - 45.000đ / 1000 lượt hiển thị
    BASE_CPM_VND: float = 35000.0
    CONVERSION_RATE_MIN: float = 0.015  # 1.5% click/message
    CONVERSION_RATE_MAX: float = 0.035  # 3.5% click/message

    def simulate(self, data: CampaignSimulationInput) -> CampaignSimulationResult:
        total_budget = data.daily_budget_vnd * data.duration_days
        impressions = (total_budget / self.BASE_CPM_VND) * 1000

        # Ước tính số người tiếp cận duy nhất (Reach)
        reach_min = int(impressions * 0.70)
        reach_max = int(impressions * 0.90)

        # Ước tính hội thoại / tương tác quan tâm
        conv_min = max(1, int(reach_min * self.CONVERSION_RATE_MIN * 0.1))
        conv_max = max(conv_min + 1, int(reach_max * self.CONVERSION_RATE_MAX * 0.1))

        return CampaignSimulationResult(
            objective=data.objective,
            radius_km=data.radius_km,
            daily_budget_vnd=data.daily_budget_vnd,
            duration_days=data.duration_days,
            total_budget_vnd=total_budget,
            estimated_reach_min=reach_min,
            estimated_reach_max=reach_max,
            estimated_conversations_min=conv_min,
            estimated_conversations_max=conv_max,
            estimated_cpm_vnd=self.BASE_CPM_VND,
            disclaimer=(
                "Ước tính mô phỏng tham khảo dựa trên CPM trung bình thị trường Việt Nam. "
                "Havi không cam kết doanh thu hay kết quả quảng cáo thực tế."
            ),
            safety_guardrails=[
                "Ngân sách quảng cáo thanh toán trực tiếp cho Meta / Facebook.",
                "Havi không giữ tiền media và không thu phí trung gian chi tiêu.",
                "Chiến dịch luôn yêu cầu người dùng bấm duyệt trước khi kích hoạt.",
                "Có nút dừng khẩn cấp (Kill Switch) ngay trên ứng dụng.",
            ],
        )
