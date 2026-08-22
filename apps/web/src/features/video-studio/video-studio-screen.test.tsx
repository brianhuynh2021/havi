import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { VideoStudioScreen } from "./video-studio-screen";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function signedIn() {
  writeTokens({
    accessToken: "test_access_token",
    refreshToken: "test_refresh_token",
    activeWorkspaceId: "ws-123",
    needsOnboarding: false,
  });
}

function renderScreen() {
  return render(
    <LanguageProvider>
      <VideoStudioScreen />
    </LanguageProvider>
  );
}

describe("VideoStudioScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hiển thị danh sách render jobs và preview canvas 9:16", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      if (url.pathname.includes("/render-jobs")) {
        return jsonResponse({
          items: [
            {
              id: "job-1",
              workspace_id: "ws-123",
              title: "TikTok Giảm Cân Siêu Tốc",
              target_aspect_ratio: "9:16",
              status: "rendering",
              progress_percent: 45,
              renderer_engine: "ffmpeg",
              source_media_id: null,
              edit_plan: {
                target_aspect_ratio: "9:16",
                target_duration_seconds: 15,
                cuts: [],
                captions: [],
              },
              output_media_id: null,
              output_url: null,
              error_message: null,
              started_at: "2026-08-15T10:00:00Z",
              completed_at: null,
              created_at: "2026-08-15T10:00:00Z",
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        });
      }
      return jsonResponse({});
    });

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("TikTok Giảm Cân Siêu Tốc")).toBeInTheDocument();
      expect(screen.getByText("rendering")).toBeInTheDocument();
    });

    expect(screen.getByText("📱 Bản Xem Trước 9:16")).toBeInTheDocument();
    expect(screen.getByText(/Studio Video Tự Động/i)).toBeInTheDocument();
  });

  it("cho phép gửi form tạo job render video mới", async () => {
    const user = userEvent.setup();
    let createdPayload: { title?: string; edit_plan?: unknown } | null = null;

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      const method = input instanceof Request ? input.method : init?.method || "GET";

      if (url.pathname.includes("/render-jobs") && method === "POST") {
        const bodyStr = input instanceof Request ? await input.clone().text() : (init?.body as string);
        createdPayload = JSON.parse(bodyStr || "{}");
        return jsonResponse({
          id: "job-2",
          workspace_id: "ws-123",
          title: createdPayload?.title || "Test Video",
          target_aspect_ratio: "9:16",
          status: "queued",
          progress_percent: 0,
          renderer_engine: "ffmpeg",
          source_media_id: null,
          edit_plan: createdPayload.edit_plan,
          output_media_id: null,
          output_url: null,
          error_message: null,
          started_at: null,
          completed_at: null,
          created_at: "2026-08-15T10:05:00Z",
        }, 201);
      }

      return jsonResponse({ items: [], total: 0, limit: 20, offset: 0 });
    });

    renderScreen();

    const titleInput = screen.getByLabelText("Tiêu đề Video");
    await user.clear(titleInput);
    await user.type(titleInput, "Reels Trà Sữa Đào");

    const submitBtn = screen.getByRole("button", { name: /Bắt đầu Dựng Video/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(createdPayload).not.toBeNull();
      expect(createdPayload.title).toBe("Reels Trà Sữa Đào");
      expect(createdPayload.target_aspect_ratio).toBe("9:16");
    });
  });

  it("hiển thị danh sách AI Trend Scout và cho phép áp dụng 1-chạm", async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      if (url.pathname.includes("/trends/hot")) {
        return jsonResponse([
          {
            id: "trend-1",
            keyword: "Học nghề 3 tháng vs Đại học 4 năm",
            category: "career_guidance",
            trend_score: 98,
            source: "TikTok Trends",
            hook_style: "real_comparison",
            sample_hook: "ĐỪNG MẤT 4 NĂM NẾU CHƯA BIẾT ĐIỀU NÀY!",
            suggested_angle: "So sánh thực tế",
            suggested_hashtags: ["#hocnghe", "#shorts"],
          },
        ]);
      }
      return jsonResponse({ items: [], total: 0, limit: 20, offset: 0 });
    });

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Học nghề 3 tháng vs Đại học 4 năm")).toBeInTheDocument();
      expect(screen.getByText(/Hot 98%/i)).toBeInTheDocument();
    });

    const applyBtn = screen.getByRole("button", { name: /Dựng Video Theo Trend Này/i });
    await user.click(applyBtn);

    const hookInput = screen.getByLabelText("3s Hook Subtitle (Chữ động giữ chân)") as HTMLInputElement;
    expect(hookInput.value).toBe("ĐỪNG MẤT 4 NĂM NẾU CHƯA BIẾT ĐIỀU NÀY!");
  });

  it("cho phép quét lại xu hướng mới khi bấm nút Quét xu hướng mới", async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      if (url.pathname.includes("/trends/refresh")) {
        return jsonResponse([
          {
            id: "trend-fresh-1",
            keyword: "Ứng dụng AI Agent tự động hóa doanh nghiệp",
            category: "tech_news",
            trend_score: 99,
            source: "Google Trends VN",
            hook_style: "warning_mistake",
            sample_hook: "DOANH NGHIỆP CỦA BẠN ĐANG MẤT TIỀN NẾU CHƯA DÙNG AI NÀY!",
            suggested_angle: "Trình diễn AI Agent",
            suggested_hashtags: ["#aiagent", "#tudonghoa"],
          },
        ]);
      }
      return jsonResponse({ items: [], total: 0, limit: 20, offset: 0 });
    });

    renderScreen();

    const refreshBtn = await screen.findByRole("button", { name: /Quét xu hướng mới/i });
    await user.click(refreshBtn);

    await waitFor(() => {
      expect(screen.getByText("Ứng dụng AI Agent tự động hóa doanh nghiệp")).toBeInTheDocument();
      expect(screen.getByText(/Hot 99%/i)).toBeInTheDocument();
    });
  });
});

