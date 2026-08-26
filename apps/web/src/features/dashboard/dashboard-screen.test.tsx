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

type Fixture = {
  summary?: Partial<{
    drafts: number;
    pending_approval: number;
    scheduled: number;
    published: number;
    failed: number;
    total_connections: number;
    broken_connections: number;
    unhandled_inbox: number;
  }>;
  connections?: Array<Record<string, unknown>>;
  inbox?: Array<Record<string, unknown>>;
  summaryFails?: boolean;
};

/**
 * Bảng điều khiển đọc **một** endpoint duy nhất — `/analytics/dashboard` đã đếm
 * sẵn kênh hỏng và hội thoại chưa xử lý ở backend.
 *
 * Fixture vẫn nhận `connections` và `inbox` dạng danh sách vì đó là cách diễn
 * đạt tự nhiên của từng ca kiểm thử ("một kênh nối, một kênh mất quyền"); hàm
 * này quy chúng về đúng con số mà backend sẽ trả. Đếm ở đây phải khớp với
 * `api/routers/analytics.py`, nếu không test xanh mà màn hình sai.
 */
function mockApi(fixture: Fixture = {}) {
  const connections = fixture.connections ?? [];
  const inbox = fixture.inbox ?? [];

  vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
    const url = new URL(input instanceof Request ? input.url : String(input));

    if (url.pathname.endsWith("/analytics/dashboard")) {
      if (fixture.summaryFails) return jsonResponse({ detail: "hỏng" }, 500);
      return jsonResponse({
        drafts: 0,
        pending_approval: 0,
        scheduled: 0,
        published: 0,
        failed: 0,
        total_connections: connections.length,
        broken_connections: connections.filter((item) => item.status !== "connected").length,
        unhandled_inbox: inbox.filter(
          (item) => item.status === "new" || item.status === "drafted",
        ).length,
        ...fixture.summary,
      });
    }
    return jsonResponse([]);
  });
}

const connectedPage = {
  platform: "facebook",
  status: "connected",
  external_account_id: "page-1",
  external_account_name: "Trang Thử",
};

beforeEach(signedIn);
afterEach(() => vi.restoreAllMocks());

describe("DashboardScreen — bảng điều khiển vận hành", () => {
  it("KHÔNG hỏi mục tiêu và KHÔNG hiện phễu lead hay doanh thu", async () => {
    mockApi({ connections: [connectedPage] });
    render(<DashboardScreen />);
    await screen.findByText(/Tổng quan/);

    const body = document.body.textContent ?? "";
    for (const word of [
      "mục tiêu",
      "Mục tiêu",
      "Lộ trình",
      "PHỄU KHÉP KÍN",
      "Doanh thu",
      "Đã chốt",
      "Khách quan tâm",
    ]) {
      expect(body).not.toContain(word);
    }
  });

  it("mọi thứ ổn thì nói thẳng là ổn, không giấu ô đi", async () => {
    mockApi({ connections: [connectedPage] });
    render(<DashboardScreen />);

    expect(await screen.findByText(/1 kênh đang hoạt động bình thường/)).toBeInTheDocument();
    expect(document.body.textContent).toContain("mọi thứ đang chạy bình thường");
    expect(screen.getByText("Không có nội dung nào chờ duyệt")).toBeInTheDocument();
    expect(screen.getByText("Không có bài nào thất bại")).toBeInTheDocument();
  });

  it("có việc thì đếm đúng số việc cần xử lý", async () => {
    mockApi({
      summary: { pending_approval: 3, failed: 2, scheduled: 5 },
      connections: [connectedPage, { ...connectedPage, platform: "tiktok", status: "revoked" }],
      inbox: [{ id: "i1", status: "new" }, { id: "i2", status: "drafted" }],
    });
    render(<DashboardScreen />);

    // Kênh hỏng + chờ duyệt + đăng lỗi + hội thoại chưa xử lý = 4.
    // Bài đã xếp lịch KHÔNG tính: chờ tới giờ là chuyện bình thường.
    expect(await screen.findByText("1 kênh cần xác thực lại")).toBeInTheDocument();
    expect(document.body.textContent).toContain("4 việc cần bạn xử lý");
    expect(screen.getByText("3 nội dung đang chờ người duyệt")).toBeInTheDocument();
    expect(screen.getByText("2 bài chưa lên được kênh")).toBeInTheDocument();
    expect(screen.getByText("2 hội thoại chưa được trả lời")).toBeInTheDocument();
    expect(screen.getByText("5 bài đã xếp lịch, chờ tới giờ")).toBeInTheDocument();
  });

  it("hội thoại đã trả lời hoặc đã bỏ qua không tính là chưa xử lý", async () => {
    mockApi({
      connections: [connectedPage],
      inbox: [{ id: "i1", status: "sent" }, { id: "i2", status: "dismissed" }],
    });
    render(<DashboardScreen />);

    expect(await screen.findByText("Không còn hội thoại nào chờ")).toBeInTheDocument();
  });

  it("chưa nối kênh nào cũng là việc cần làm, không phải trạng thái yên ổn", async () => {
    mockApi({ connections: [] });
    render(<DashboardScreen />);

    expect(await screen.findByText(/Chưa nối kênh nào/)).toBeInTheDocument();
    expect(document.body.textContent).toContain("1 việc cần bạn xử lý");
  });

  it("chỉ gọi ĐÚNG MỘT request để dựng cả bảng", async () => {
    // Bản trước gọi ba API rồi đếm bằng JS ở trình duyệt: tải cả danh sách kết
    // nối và cả hộp thư về chỉ để lấy hai con số. Hộp thư vài trăm hội thoại là
    // màn được mở nhiều nhất trở thành màn nặng nhất.
    mockApi({ summary: { pending_approval: 2 } });
    render(<DashboardScreen />);
    await screen.findByText("2 nội dung đang chờ người duyệt");

    const calls = vi.mocked(globalThis.fetch).mock.calls;
    expect(calls).toHaveLength(1);
    const [input] = calls[0];
    expect(input instanceof Request ? input.url : String(input)).toContain(
      "/analytics/dashboard",
    );
  });

  it("số liệu chính hỏng thì báo lỗi kèm nút thử lại, không hiện số bịa", async () => {
    mockApi({ summaryFails: true });
    render(<DashboardScreen />);

    expect(await screen.findByRole("button", { name: /Thử lại/ })).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("Không có bài nào thất bại");
  });

  it("ô đang yên ổn KHÔNG có link — bấm vào chỉ tới danh sách rỗng", async () => {
    mockApi({ connections: [connectedPage] });
    render(<DashboardScreen />);
    await screen.findByText("Không có bài nào thất bại");

    // "Xem lý do →" dưới dòng "Không có bài nào thất bại" là ngõ cụt.
    expect(screen.queryByText(/Xem lý do/)).toBeNull();
    expect(screen.queryByText(/Mở Hội thoại/)).toBeNull();
  });

  it("ô có việc thì vẫn có link để đi xử lý", async () => {
    mockApi({ summary: { failed: 2 }, connections: [connectedPage] });
    render(<DashboardScreen />);

    expect(await screen.findByText(/Xem lý do/)).toBeInTheDocument();
  });

  it("chưa nối kênh nào: đếm 0 nhưng VẪN có link, vì đó là việc cần làm", async () => {
    mockApi({ connections: [] });
    render(<DashboardScreen />);

    expect(await screen.findByText(/Chưa nối kênh nào/)).toBeInTheDocument();
    expect(screen.getByText(/Mở Kênh kết nối/)).toBeInTheDocument();
  });
});
