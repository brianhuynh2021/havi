import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { DashboardScreen } from "./dashboard-screen";

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

function event(overrides: Record<string, unknown> = {}) {
  return {
    id: "e1",
    workspace_id: "w1",
    job_id: "11111111-1111-1111-1111-111111111111",
    request_id: null,
    job_kind: "publish.run_job",
    input_summary: "raw post body should not be shown",
    output_summary: "external id should not be shown",
    tokens_in: 0,
    tokens_out: 0,
    provider: "facebook",
    duration_ms: 120,
    error: null,
    created_at: "2026-08-11T03:00:00Z",
    ...overrides,
  };
}

function mockDashboard({
  summary,
  events = [],
  summaryStatus = 200,
  eventsStatus = 200,
}: {
  summary: unknown;
  events?: unknown[];
  summaryStatus?: number;
  eventsStatus?: number;
}) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input: RequestInfo | URL) => {
      const request = input instanceof Request ? input : new Request(input);
      const url = new URL(request.url);
      if (url.pathname.includes("/analytics/events")) {
        return jsonResponse(
          { items: events, total: events.length, limit: 5, offset: 0 },
          eventsStatus,
        );
      }
      return jsonResponse(summary, summaryStatus);
    });
}

describe("DashboardScreen", () => {
  beforeEach(() => {
    window.localStorage.clear();
    signedIn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hiện số liệu thật từ analytics dashboard", async () => {
    mockDashboard({
      summary: {
        drafts: 0,
        pending_approval: 4,
        scheduled: 2,
        published: 3,
        failed: 1,
      },
      events: [event()],
    });

    render(<DashboardScreen />);

    expect(await screen.findByText("4")).toBeInTheDocument();
    expect(screen.getByText("bài chờ duyệt")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("bài đã lên lịch")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("bài đăng lỗi")).toBeInTheDocument();
    expect(screen.getByText(/một bài đã đăng thành công/i)).toBeInTheDocument();
  });

  it("workspace rỗng không render activity fixture", async () => {
    mockDashboard({
      summary: {
        drafts: 0,
        pending_approval: 0,
        scheduled: 0,
        published: 0,
        failed: 0,
      },
    });

    render(<DashboardScreen />);

    expect(await screen.findByText(/chưa có việc nào đang chờ/i)).toBeInTheDocument();
    expect(screen.getByText(/chưa có hoạt động gần đây/i)).toBeInTheDocument();
    expect(screen.queryByText(/chị Mai hỏi giá/i)).not.toBeInTheDocument();
    expect(screen.queryByText("Đã bật")).not.toBeInTheDocument();
  });

  it("activity feed lấy event thật nhưng không lộ raw summary kỹ thuật", async () => {
    mockDashboard({
      summary: {
        drafts: 0,
        pending_approval: 0,
        scheduled: 0,
        published: 1,
        failed: 1,
      },
      events: [
        event({
          id: "e1",
          job_kind: "content.approve",
          input_summary: "approved_by=user@example.com",
        }),
        event({
          id: "e2",
          job_kind: "publish.run_job",
          error: "Graph API token expired",
          output_summary: "auth_permission page-1",
        }),
      ],
    });

    render(<DashboardScreen />);

    expect(
      await screen.findByText(/một bài đã được duyệt và đưa vào lịch đăng/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/một bài chưa đăng được/i)).toBeInTheDocument();
    expect(screen.getByText("Đã duyệt")).toBeInTheDocument();
    expect(screen.getByText("Lỗi đăng")).toBeInTheDocument();
    expect(screen.queryByText(/user@example.com/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/graph api token expired/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/auth_permission/i)).not.toBeInTheDocument();
  });

  it("activity feed lỗi riêng thì tổng quan vẫn hiển thị", async () => {
    mockDashboard({
      summary: {
        drafts: 0,
        pending_approval: 2,
        scheduled: 0,
        published: 0,
        failed: 0,
      },
      eventsStatus: 500,
    });

    render(<DashboardScreen />);

    expect(await screen.findByText("2")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/hoạt động gần đây/i);
  });

  it("lỗi mạng thì báo rõ và cho thử lại", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fail"));

    render(<DashboardScreen />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /không kết nối được/i,
    );
    expect(screen.getByRole("button", { name: /thử lại/i })).toBeInTheDocument();
  });
});
