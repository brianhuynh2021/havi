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

function mockSummary(body: unknown, status = 200) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => jsonResponse(body, status));
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
    mockSummary({
      drafts: 0,
      pending_approval: 4,
      scheduled: 2,
      published: 3,
      failed: 1,
    });

    render(<DashboardScreen />);

    expect(await screen.findByText("4")).toBeInTheDocument();
    expect(screen.getByText("bài chờ duyệt")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("bài đã lên lịch")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("bài đăng lỗi")).toBeInTheDocument();
    expect(screen.getByText(/3 bài đã đăng thành công/i)).toBeInTheDocument();
  });

  it("workspace rỗng không render activity fixture", async () => {
    mockSummary({
      drafts: 0,
      pending_approval: 0,
      scheduled: 0,
      published: 0,
      failed: 0,
    });

    render(<DashboardScreen />);

    expect(await screen.findByText(/chưa có việc nào đang chờ/i)).toBeInTheDocument();
    expect(screen.getByText(/chưa có bài đã đăng/i)).toBeInTheDocument();
    expect(screen.queryByText(/chị Mai hỏi giá/i)).not.toBeInTheDocument();
    expect(screen.queryByText("Đã bật")).not.toBeInTheDocument();
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
