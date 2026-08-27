import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { ReportsScreen } from "./reports-screen";

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

function renderReports() {
  return render(
    <LanguageProvider>
      <ReportsScreen />
    </LanguageProvider>
  );
}

function mockReports(summaryOverrides: Record<string, number> = {}) {
  const asked: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(
    async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      asked.push(url.pathname);
      if (url.pathname.endsWith("/summary")) {
        return jsonResponse({
          published_posts: 5,
          inbox_items: 2,
          replies_sent: 1,
          failed_posts: 0,
          ...summaryOverrides,
          change_vs_previous_period: {},
        });
      }
      if (url.pathname.endsWith("/timeseries")) {
        return jsonResponse({
          metric: "published_posts",
          points: [
            { period: "2026-W29", value: 0 },
            { period: "2026-W30", value: 2 },
            { period: "2026-W31", value: 1 },
            { period: "2026-W32", value: 2 },
          ],
        });
      }
      if (url.pathname.endsWith("/failed-posts")) return jsonResponse([]);
      if (url.pathname.includes("/response-metrics")) {
        return jsonResponse({
          replied_count: 1,
          avg_response_seconds: 120,
          p95_response_seconds: 120,
          waiting_over_1h: 0,
          waiting_over_4h: 0,
          missed_costly: 0,
        });
      }
      if (url.pathname.endsWith("/calendar") || url.pathname.includes("/calendar")) {
        return jsonResponse({
          start: "2026-08-01",
          end: "2026-08-31",
          days: [
            {
              date: "2026-08-20",
              items: [
                {
                  id: "item-1",
                  channel: "facebook_page",
                  text: "Khai giảng khóa Lập trình Web Fullstack tại Trung Tâm Nhật Minh!",
                  status: "published",
                  scheduled_at: "2026-08-20T10:00:00Z",
                },
              ],
            },
          ],
        });
      }
      return jsonResponse([
        {
          channel: "facebook_page",
          posts: 5,
          share: 1,
          note: "Tạm tính theo bài đã đăng",
        },
      ]);
    },
  );
  return asked;
}

describe("ReportsScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hiện báo cáo từ analytics API thật", async () => {
    const asked = mockReports();

    renderReports();

    // "5" xuất hiện ở cả thẻ "Việc Havi đã làm" lẫn ô thống kê — đúng số liệu
    // thật từ API, nên khẳng định số lần xuất hiện thay vì đòi duy nhất một.
    expect((await screen.findAllByText("5")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Bài đã đăng")).toBeInTheDocument();
    expect(screen.getAllByText("Hội thoại đã nhận").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Facebook Page").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Khai giảng khóa Lập trình Web/i)).toBeInTheDocument();
    await waitFor(() =>
      expect(asked).toEqual(
        expect.arrayContaining([
          "/analytics/summary",
          "/analytics/timeseries",
          "/analytics/attribution",
        ]),
      ),
    );
  });

  it("workspace rỗng không hiện claim fixture về reach hay Google Maps", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input: RequestInfo | URL) => {
        const url = new URL(input instanceof Request ? input.url : String(input));
        if (url.pathname.endsWith("/summary")) {
          return jsonResponse({
            published_posts: 0,
            inbox_items: 0,
            replies_sent: 0,
            failed_posts: 0,
            change_vs_previous_period: {},
          });
        }
        if (url.pathname.endsWith("/timeseries")) {
          return jsonResponse({
            metric: "published_posts",
            points: [
              { period: "2026-W29", value: 0 },
              { period: "2026-W30", value: 0 },
              { period: "2026-W31", value: 0 },
              { period: "2026-W32", value: 0 },
            ],
          });
        }
        return jsonResponse([]);
      },
    );

    renderReports();

    expect(await screen.findByText(/chưa có bài đã đăng/i)).toBeInTheDocument();
    expect(screen.queryByText(/lượt tiếp cận/i)).not.toBeInTheDocument();
  });

  it("lỗi mạng thì báo rõ và cho thử lại", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fail"));

    renderReports();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /không kết nối được/i,
    );
    expect(screen.getByRole("button", { name: /thử lại/i })).toBeInTheDocument();
  });

  it("chưa có dữ liệu thì nói thẳng, không hiện số liệu mẫu", async () => {
    mockReports({ published_posts: 0, inbox_items: 0 });

    renderReports();

    expect(await screen.findByText(/CHƯA ĐỦ DỮ LIỆU/)).toBeInTheDocument();

    // Ba lời hứa hard-code của bản trước, không cái nào được đo:
    //   "~N giờ Havi đã gánh vác"  — nhân 1,5 giờ/bài, và Math.max(1,…) khiến
    //                                nó hiện "~1 giờ" cả khi chưa có bài nào
    //   "< 10 giây phản hồi"        — chưa bao giờ đo tốc độ trả lời
    //   "100% đúng giọng thương hiệu" — chưa bao giờ chấm giọng văn
    expect(screen.queryByText(/đã gánh vác/)).toBeNull();
    expect(screen.queryByText(/10 giây/)).toBeNull();
    expect(screen.queryByText(/giọng văn thương hiệu/)).toBeNull();
  });
});
