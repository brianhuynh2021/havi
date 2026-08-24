import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { TodayScreen } from "./today-screen";

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

function renderToday() {
  return render(
    <LanguageProvider>
      <TodayScreen />
    </LanguageProvider>
  );
}

describe("TodayScreen (Havi 3.0)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hiển thị ô kêu gọi thiết lập mục tiêu khi chưa có goal", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input), "http://localhost:8000");
      if (url.pathname.includes("/goals/active")) {
        return jsonResponse(null, 404);
      }
      if (url.pathname.includes("/roadmaps/active") || url.pathname.includes("/roadmaps/today")) {
        return jsonResponse(null, 404);
      }
      return jsonResponse({});
    });

    renderToday();

    expect(await screen.findByText(/Hôm nay cùng Havi/i)).toBeInTheDocument();
    expect(screen.getByText(/Bạn muốn ưu tiên đạt kết quả gì tiếp theo/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Bắt đầu kế hoạch \(1 chạm\)/i)[0]).toBeInTheDocument();
  });

  it("hiển thị hành động đề xuất hôm nay khi đã có mục tiêu và lộ trình", async () => {
    const mockGoal = {
      id: "g1",
      workspace_id: "w1",
      title: "Tuyển sinh 20 học viên AI",
      category: "acquire_customers",
      evidence_definition: "Học viên đóng tiền VietQR",
      status: "active",
      weekly_capacity_hours: 10,
    };

    const mockTask = {
      id: "t1",
      workspace_id: "w1",
      roadmap_id: "r1",
      goal_id: "g1",
      title: "Soạn bài viết ưu đãi tuyển sinh",
      why_this_is_next: "Cần thông điệp rõ ràng trước khi tiếp cận học viên",
      done_rule: "Có 1 bài viết nêu rõ học phí và lịch học",
      time_estimate_minutes: 25,
      owner_type: "collaborative",
      capability_module: "content",
      status: "pending",
      order_index: 0,
    };

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input), "http://localhost:8000");
      if (url.pathname.includes("/goals/active")) {
        return jsonResponse(mockGoal);
      }
      if (url.pathname.includes("/roadmaps/active")) {
        return jsonResponse({
          roadmap: {
            id: "r1",
            workspace_id: "w1",
            goal_id: "g1",
            version: 1,
            title: "Lộ trình tuyển sinh",
            horizon_90d: "90d plan",
            horizon_30d: "30d plan",
            horizon_7d: "7d plan",
            status: "active",
            confidence_score: 0.88,
          },
          tasks: [mockTask],
        });
      }
      if (url.pathname.includes("/roadmaps/today")) {
        return jsonResponse(mockTask);
      }
      return jsonResponse({});
    });

    renderToday();

    expect(await screen.findByText(/Tuyển sinh 20 học viên AI/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Soạn bài viết ưu đãi tuyển sinh/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/Cần thông điệp rõ ràng trước khi tiếp cận học viên/i)).toBeInTheDocument();
    expect(screen.getByText(/Đã làm xong việc này/i)).toBeInTheDocument();
    expect(screen.getByText(/Cần đổi cách làm khác/i)).toBeInTheDocument();
  });

  it("hiển thị đầy đủ 3 Thẻ Tác Chiến (Trực Chiến 24/7, Săn Khách & Doanh Thu, Clip Thật 10s)", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input), "http://localhost:8000");
      if (url.pathname.includes("/inbox")) {
        return jsonResponse({ items: [] });
      }
      if (url.pathname.includes("/leads")) {
        return jsonResponse({ items: [] });
      }
      if (url.pathname.includes("/goals/active")) {
        return jsonResponse(null, 404);
      }
      return jsonResponse({});
    });

    renderToday();

    // 1. Thẻ Trực chiến
    expect(await screen.findByText(/Bảng Điều Khiển Tác Chiến Hôm Nay/i)).toBeInTheDocument();
    expect(screen.getByText(/TRỰC CHIẾN 24\/7/i)).toBeInTheDocument();
    expect(screen.getByText(/AI Guard Mode Đang Bật/i)).toBeInTheDocument();

    // 2. Thẻ Doanh thu & Săn khách
    expect(screen.getByText(/DOANH THU & SĂN KHÁCH/i)).toBeInTheDocument();
    expect(screen.getByText(/Săn 10 Khách Đầu Tiên \(Day 0\)/i)).toBeInTheDocument();

    // 3. Thẻ Clip Thật
    expect(screen.getByText(/CLIP THẬT 10S/i)).toBeInTheDocument();
    expect(screen.getByText(/Quay 10-15s clip thật tại cơ sở và thả vào đây/i)).toBeInTheDocument();
  });
});



