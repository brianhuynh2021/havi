import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { simulateCampaign } from "./campaign.api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function signedIn() {
  writeTokens({
    accessToken: "at",
    refreshToken: "rt",
    activeWorkspaceId: "w1",
    needsOnboarding: false,
  });
}

describe("campaign.api (Phase 5)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("gửi request mô phỏng chiến dịch và nhận kết quả ước tính minh bạch", async () => {
    const mockResult = {
      objective: "messages",
      radius_km: 5,
      daily_budget_vnd: 100000,
      duration_days: 7,
      total_budget_vnd: 700000,
      estimated_reach_min: 14000,
      estimated_reach_max: 18000,
      estimated_conversations_min: 21,
      estimated_conversations_max: 63,
      estimated_cpm_vnd: 35000,
      disclaimer: "Ước tính mô phỏng tham khảo dựa trên CPM trung bình thị trường Việt Nam.",
      safety_guardrails: ["Ngân sách quảng cáo thanh toán trực tiếp cho Meta"],
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(jsonResponse(mockResult));

    const res = await simulateCampaign({
      objective: "messages",
      radius_km: 5,
      daily_budget_vnd: 100000,
      duration_days: 7,
    });

    expect(res.ok).toBe(true);
    if (res.ok) {
      expect(res.data.total_budget_vnd).toBe(700000);
      expect(res.data.estimated_reach_min).toBe(14000);
      expect(res.data.disclaimer).toContain("Ước tính mô phỏng");
    }
  });
});
