import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { CoachScreen } from "./coach-screen";

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

function renderCoach() {
  return render(
    <LanguageProvider>
      <CoachScreen />
    </LanguageProvider>
  );
}

describe("CoachScreen (Phase 3)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("gắn chặt bối cảnh vào mục tiêu và việc hôm nay", async () => {
    const mockGoal = {
      id: "g1",
      workspace_id: "w1",
      title: "Tuyển sinh 20 học viên AI",
      category: "acquire_customers",
      evidence_definition: "Học viên đóng tiền VietQR",
      status: "active",
      weekly_capacity_hours: 10,
    };

    const mockRoadmapData = {
      roadmap: {
        id: "r1",
        version: 1,
        title: "Lộ trình tuyển sinh",
        horizon_90d: "90 ngày",
        horizon_30d: "30 ngày",
        horizon_7d: "7 ngày",
        assumptions: [],
        confidence_score: 0.9,
      },
      tasks: [
        {
          id: "t1",
          title: "Soạn ưu đãi tuyển sinh",
          why_this_is_next: "Cần lời mời rõ ràng",
          done_rule: "Có 1 bài viết",
          status: "pending",
          order_index: 0,
        },
      ],
    };

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input), "http://localhost:8000");
      if (url.pathname.includes("/goals/active")) {
        return jsonResponse(mockGoal);
      }
      if (url.pathname.includes("/roadmaps/active")) {
        return jsonResponse(mockRoadmapData);
      }
      return jsonResponse({});
    });

    renderCoach();

    expect(await screen.findByText(/Havi Đồng Hành/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Tuyển sinh 20 học viên AI/i).length).toBeGreaterThanOrEqual(1);

    const user = userEvent.setup();

    const promptBtn = screen.getByRole("button", { name: /việc ưu tiên hôm nay/i });
    await user.click(promptBtn);

    expect(await screen.findByText(/Soạn ưu đãi tuyển sinh/i)).toBeInTheDocument();
  });
});
