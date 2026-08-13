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

function mockReports() {
  const asked: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(
    async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      asked.push(url.pathname);
      if (url.pathname.endsWith("/summary")) {
        return jsonResponse({
          price_inquiries: 0,
          walk_ins: 0,
          returning_customers: 0,
          published_posts: 5,
          new_leads: 0,
          lead_won_rate: 0,
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
      return jsonResponse([
        {
          channel: "facebook_page",
          customers: 5,
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

    expect(await screen.findByText("5")).toBeInTheDocument();
    expect(screen.getByText("Bài đã đăng")).toBeInTheDocument();
    expect(screen.getByText("Khách tiềm năng")).toBeInTheDocument();
    expect(screen.getByText("Facebook Page")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
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
            price_inquiries: 0,
            walk_ins: 0,
            returning_customers: 0,
            published_posts: 0,
            new_leads: 0,
            lead_won_rate: 0,
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
});
