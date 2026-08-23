import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { RoadmapScreen } from "./roadmap-screen";

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

describe("RoadmapScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hiển thị trạng thái chưa có mục tiêu và nút tạo mục tiêu 1 chạm", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input), "http://localhost:8000");
      if (url.pathname.includes("/goals/active")) {
        return jsonResponse(null, 404);
      }
      return jsonResponse({});
    });

    render(
      <LanguageProvider>
        <RoadmapScreen />
      </LanguageProvider>
    );

    expect(await screen.findByText(/Chưa có mục tiêu nào được tạo/i)).toBeInTheDocument();
    expect(screen.getByText(/Tạo Mục Tiêu Đầu Tiên/i)).toBeInTheDocument();
  });

  it("hiển thị lộ trình và danh sách nhiệm vụ khi đã có mục tiêu", async () => {
    const mockGoal = {
      id: "g1",
      workspace_id: "w1",
      title: "Tuyển sinh 20 học viên AI",
      category: "acquire_customers",
      evidence_definition: "Học viên đóng tiền VietQR",
      status: "active",
      weekly_capacity_hours: 10,
    };

    const mockRoadmap = {
      roadmap: {
        id: "r1",
        workspace_id: "w1",
        goal_id: "g1",
        version: 1,
        title: "Lộ trình tuyển sinh",
        horizon_90d: "90 ngày",
        horizon_30d: "30 ngày",
        horizon_7d: "7 ngày",
        status: "active",
        confidence_score: 0.9,
      },
      tasks: [
        {
          id: "t1",
          workspace_id: "w1",
          roadmap_id: "r1",
          goal_id: "g1",
          title: "Soạn kịch bản video AI",
          why_this_is_next: "Để chuẩn bị quay video ngắn",
          done_rule: "Có 1 kịch bản hoàn chỉnh",
          time_estimate_minutes: 20,
          owner_type: "collaborative",
          capability_module: "video",
          status: "pending",
          order_index: 0,
        },
      ],
    };

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input), "http://localhost:8000");
      if (url.pathname.includes("/goals/active")) return jsonResponse(mockGoal);
      if (url.pathname.includes("/roadmaps/active")) return jsonResponse(mockRoadmap);
      if (url.pathname.includes("/roadmaps/history")) return jsonResponse([]);
      return jsonResponse({});
    });

    render(
      <LanguageProvider>
        <RoadmapScreen />
      </LanguageProvider>
    );

    expect(await screen.findByText(/Tuyển sinh 20 học viên AI/i)).toBeInTheDocument();
    expect(screen.getByText(/Soạn kịch bản video AI/i)).toBeInTheDocument();
    expect(screen.getByText(/Đổi mục tiêu/i)).toBeInTheDocument();
  });
});
