import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { QuotaBanner } from "./quota-banner";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function quota(overrides: Record<string, unknown> = {}) {
  return {
    used: 1_000,
    limit: 100_000,
    remaining: 99_000,
    near_limit: false,
    exceeded: false,
    resets_at: "2026-09-01T00:00:00Z",
    ...overrides,
  };
}

function mockQuota(body: unknown, status = 200) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => jsonResponse(body, status));
}

describe("QuotaBanner", () => {
  beforeEach(() => {
    window.localStorage.clear();
    writeTokens({
      accessToken: "a",
      refreshToken: "r",
      activeWorkspaceId: "w1",
      needsOnboarding: false,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("còn nhiều quota thì ẩn hẳn, không chiếm chỗ ô nạp liệu", async () => {
    mockQuota(quota());
    const { container } = render(<QuotaBanner />);

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it("gần hết thì cảnh báo trước, vẫn cho làm việc bình thường", async () => {
    // 20k token còn lại ≈ 5 bài. Cảnh báo TRƯỚC khi bị chặn là cả mục đích của
    // banner này — chặn giữa lúc chủ tiệm đang cần đăng bài mới là tệ.
    mockQuota(quota({ used: 80_000, remaining: 20_000, near_limit: true }));
    render(<QuotaBanner />);

    expect(await screen.findByText(/còn khoảng 5 bài/i)).toBeInTheDocument();
    // Cảnh báo, không phải lỗi — dùng role="status" để screen reader không ngắt lời.
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("hết quota thì nói rõ bài đã duyệt VẪN đăng đúng lịch", async () => {
    // Chủ tiệm sợ nhất là "hết quota = mọi thứ dừng". Sự thật là chỉ chặn tạo bài
    // mới; bài đã duyệt vẫn lên đúng giờ. Không nói ra thì họ hoảng.
    mockQuota(quota({ used: 100_000, remaining: 0, exceeded: true }));
    render(<QuotaBanner />);

    expect(await screen.findByText(/hết lượt tạo bài/i)).toBeInTheDocument();
    expect(screen.getByText(/vẫn đăng đúng lịch/i)).toBeInTheDocument();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("nói rõ ngày quota mở lại, theo giờ VN", async () => {
    // resets_at là 00:00 ngày 1/9 giờ VN = 2026-08-31T17:00:00Z.
    // Format theo giờ máy sẽ ra 31/08 ở nhiều múi giờ — sai một ngày.
    mockQuota(
      quota({ exceeded: true, remaining: 0, resets_at: "2026-08-31T17:00:00Z" }),
    );
    render(<QuotaBanner />);

    expect(await screen.findByText(/01\/09/)).toBeInTheDocument();
  });

  it("số bài còn lại không bao giờ là 0 khi vẫn còn quota", async () => {
    // Còn 100 token thì làm tròn xuống ra 0 bài — nói "còn 0 bài" trong lúc chưa
    // bị chặn là mâu thuẫn với chính nút "Để Havi viết" vẫn bấm được.
    mockQuota(quota({ used: 99_900, remaining: 100, near_limit: true }));
    render(<QuotaBanner />);

    expect(await screen.findByText(/còn khoảng 1 bài/i)).toBeInTheDocument();
  });

  it("API hỏng thì ẩn banner, không hiện lỗi", async () => {
    // Quota là thông tin phụ trợ. Hiện "không tải được quota" chỉ làm chủ tiệm lo
    // trong khi họ vẫn tạo bài được bình thường.
    mockQuota({ detail: "loi" }, 500);
    const { container } = render(<QuotaBanner />);

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
