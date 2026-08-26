import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { MorningBrief } from "./morning-brief";
import { formatMinutes } from "./queue.api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function brief(overrides: Record<string, unknown> = {}) {
  return {
    generated_at: "2026-08-26T01:00:00Z",
    window_hours: 24,
    activity: {
      published: 3,
      inbox_received: 14,
      replies_sent: 11,
      publish_failed: 0,
    },
    attention_total: 6,
    attention_costly: 4,
    calendar_gaps: [
      { date: "2026-08-27", weekday: "Thứ Năm" },
      { date: "2026-08-30", weekday: "Chủ Nhật" },
    ],
    time_saved_minutes: 31,
    time_saved_actions: [
      { action: "Trả lời khách", count: 11, minutes_each: 2, minutes_total: 22 },
      { action: "Đăng bài lên kênh", count: 3, minutes_each: 3, minutes_total: 9 },
    ],
    ...overrides,
  };
}

function mockBrief(body: unknown = brief(), status = 200) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => jsonResponse(body, status));
}

beforeEach(() => {
  window.localStorage.clear();
  writeTokens({
    accessToken: "at",
    refreshToken: "rt",
    activeWorkspaceId: "w1",
    needsOnboarding: false,
  });
});

afterEach(() => vi.restoreAllMocks());

describe("MorningBrief", () => {
  it("mặc định thu gọn — người mở app mỗi ngày tới để làm việc, không đọc báo cáo", async () => {
    mockBrief();
    render(<MorningBrief />);

    expect(await screen.findByText(/3 bài đã lên kênh/)).toBeInTheDocument();
    // Phần chi tiết chưa mở.
    expect(screen.queryByText(/Havi làm thay bạn/)).toBeNull();
  });

  it("mở ra thì hiện PHÉP TÍNH thời gian tiết kiệm, không chỉ con số tổng", async () => {
    // Con số tổng mà ẩn giả định thì nó là quảng cáo, không phải số liệu. Khách
    // thấy được phép tính thì họ tự kiểm và tin.
    mockBrief();
    render(<MorningBrief />);
    fireEvent.click(await screen.findByRole("button"));

    expect(screen.getByText(/Havi làm thay bạn/)).toBeInTheDocument();
    expect(screen.getByText(/11 × 2 phút = 22 phút/)).toBeInTheDocument();
    expect(screen.getByText(/3 × 3 phút = 9 phút/)).toBeInTheDocument();
    expect(screen.getByText(/Chỉ đếm việc Havi thật sự đã làm/)).toBeInTheDocument();
  });

  it("nói rõ bao nhiêu việc bỏ sót là mất khách", async () => {
    mockBrief();
    render(<MorningBrief />);
    fireEvent.click(await screen.findByRole("button"));

    expect(screen.getByText(/6/)).toBeInTheDocument();
    expect(screen.getByText(/việc bỏ sót là mất khách/)).toBeInTheDocument();
  });

  it("hiện ngày trống lịch bằng thứ, không bằng ngày tháng", async () => {
    // "Thứ Năm chưa có bài" hành động được; "2026-08-27 chưa có bài" thì phải
    // tra lịch mới biết đó là hôm nào.
    mockBrief();
    render(<MorningBrief />);
    fireEvent.click(await screen.findByRole("button"));

    expect(screen.getByText("Thứ Năm")).toBeInTheDocument();
    expect(screen.getByText("Chủ Nhật")).toBeInTheDocument();
  });

  it("lịch đủ bảy ngày thì nói thẳng là đủ, không ẩn khối đi", async () => {
    mockBrief(brief({ calendar_gaps: [] }));
    render(<MorningBrief />);
    fireEvent.click(await screen.findByRole("button"));

    expect(screen.getByText(/Bảy ngày tới đã có bài mỗi ngày/)).toBeInTheDocument();
  });

  it("24 giờ im lặng thì nói im lặng, không hiện một dãy số 0", async () => {
    mockBrief(
      brief({
        activity: { published: 0, inbox_received: 0, replies_sent: 0, publish_failed: 0 },
        time_saved_minutes: 0,
      }),
    );
    render(<MorningBrief />);

    expect(await screen.findByText(/không có hoạt động nào/)).toBeInTheDocument();
  });

  it("có bài lỗi thì tô riêng ngay ở dòng thu gọn", async () => {
    mockBrief(
      brief({
        activity: { published: 2, inbox_received: 5, replies_sent: 5, publish_failed: 2 },
      }),
    );
    render(<MorningBrief />);

    expect(await screen.findByText(/2 bài lỗi/)).toBeInTheDocument();
  });

  it("bản tin hỏng thì IM LẶNG, không che mất hàng đợi bằng banner lỗi", async () => {
    // Bản tin là phần phụ trợ trên hàng đợi. Một banner lỗi ở đây sẽ đẩy việc
    // cần làm xuống dưới — thứ người dùng vào đây để làm.
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fail"));
    const { container } = render(<MorningBrief />);

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(container.textContent).toBe("");
  });

  it("KHÔNG hiện chỉ số Havi không đo được", async () => {
    // Doanh thu từ social, engagement theo nền tảng, động thái đối thủ — ba câu
    // hấp dẫn nhất và Havi không có dữ liệu nào cho cả ba.
    mockBrief();
    render(<MorningBrief />);
    fireEvent.click(await screen.findByRole("button"));

    const body = document.body.textContent ?? "";
    for (const banned of ["doanh thu", "Doanh thu", "engagement", "đối thủ", "follower"]) {
      expect(body).not.toContain(banned);
    }
  });
});

describe("formatMinutes", () => {
  it("dưới một giờ thì nói bằng phút, không '0 giờ 40 phút'", () => {
    expect(formatMinutes(40)).toBe("40 phút");
    expect(formatMinutes(0)).toBe("0 phút");
  });

  it("tròn giờ thì bỏ phần phút", () => {
    expect(formatMinutes(120)).toBe("2 giờ");
  });

  it("lẻ thì nói cả hai", () => {
    expect(formatMinutes(402)).toBe("6 giờ 42 phút");
  });
});
