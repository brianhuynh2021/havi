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
    silent_channels: [
      {
        channel: "reels",
        label: "Facebook Reels",
        days: 12,
        ever_published: false,
      },
      {
        channel: "facebook_page",
        label: "Facebook — bài trên Trang",
        days: 6,
        ever_published: true,
      },
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
  it("mặc định mở để Time Havi Saved không bị giấu", async () => {
    mockBrief();
    render(<MorningBrief />);

    expect(await screen.findByText(/3 bài đã đăng/)).toBeInTheDocument();
    expect(screen.getByText(/Havi đã tiết kiệm 31 phút/)).toBeInTheDocument();
  });

  it("hiện phép tính thời gian tiết kiệm và vẫn cho phép thu gọn", async () => {
    // Con số tổng mà ẩn giả định thì nó là quảng cáo, không phải số liệu. Khách
    // thấy được phép tính thì họ tự kiểm và tin.
    mockBrief();
    render(<MorningBrief />);
    const toggle = await screen.findByRole("button");

    expect(screen.getByText(/Havi đã tiết kiệm 31 phút/)).toBeInTheDocument();
    expect(screen.getByText(/11 × 2 phút = 22 phút/)).toBeInTheDocument();
    expect(screen.getByText(/3 × 3 phút = 9 phút/)).toBeInTheDocument();
    expect(screen.getByText(/Chỉ đếm việc Havi thật sự đã làm/)).toBeInTheDocument();
    fireEvent.click(toggle);
    expect(screen.queryByText(/Havi đã tiết kiệm 31 phút/)).toBeNull();
  });

  it("nói rõ bao nhiêu việc bỏ sót là mất khách", async () => {
    mockBrief();
    render(<MorningBrief />);
    await screen.findByRole("button");

    // Khớp cả con số VỚI nhãn của nó: `/6/` trần khớp bất kỳ chỗ nào có chữ 6
    // trên màn, nên nó vẫn xanh khi con số này biến mất.
    expect(screen.getByText(/6\s*việc đang chờ/)).toBeInTheDocument();
    expect(screen.getByText(/4\s*việc bỏ sót là mất khách/)).toBeInTheDocument();
  });

  it("hiện ngày trống lịch bằng thứ, không bằng ngày tháng", async () => {
    // "Thứ Năm chưa có bài" hành động được; "2026-08-27 chưa có bài" thì phải
    // tra lịch mới biết đó là hôm nào.
    mockBrief();
    render(<MorningBrief />);
    await screen.findByRole("button");

    expect(screen.getByText("Thứ Năm")).toBeInTheDocument();
    expect(screen.getByText("Chủ Nhật")).toBeInTheDocument();
  });

  it("lịch đủ bảy ngày thì nói thẳng là đủ, không ẩn khối đi", async () => {
    mockBrief(brief({ calendar_gaps: [] }));
    render(<MorningBrief />);
    await screen.findByRole("button");

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

    expect(await screen.findByText(/chưa ghi nhận hoạt động nào/)).toBeInTheDocument();
  });

  it("có bài lỗi thì tô riêng ngay ở dòng thu gọn", async () => {
    mockBrief(
      brief({
        activity: { published: 2, inbox_received: 5, replies_sent: 5, publish_failed: 2 },
      }),
    );
    render(<MorningBrief />);

    expect(await screen.findByText(/2 bài đăng lỗi/)).toBeInTheDocument();
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
    await screen.findByRole("button");

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
  it("hiện kênh đang mở mà lâu chưa đăng, kèm số ngày", async () => {
    // Cùng loại dữ liệu với chỗ trống lịch và cũng rẻ như thế: đếm bằng SQL, không
    // cần quyền insights. Đây là điều đáng nói mà Havi biết CHẮC.
    mockBrief();
    render(<MorningBrief />);

    await screen.findByRole("button");

    expect(screen.getByText(/2\s*kênh đang mở nhưng lâu chưa đăng/)).toBeInTheDocument();
    expect(screen.getByText("Facebook — bài trên Trang")).toBeInTheDocument();
    expect(screen.getByText(/6\s*ngày chưa đăng/)).toBeInTheDocument();
  });

  it("phân biệt 'nhịp bị hụt' với 'chưa bao giờ dùng kênh này'", async () => {
    // "12 ngày chưa đăng" và "nối 12 ngày rồi chưa đăng bài nào" là hai tình
    // huống khác nhau. Gộp lại thì người đọc không biết mình đang nhìn cái nào.
    mockBrief();
    render(<MorningBrief />);

    await screen.findByRole("button");

    expect(screen.getByText(/nối\s*12\s*ngày, chưa đăng bài nào/)).toBeInTheDocument();
  });

  it("KHÔNG suy diễn hệ quả mà Havi không đo được", async () => {
    // Havi không có quyền insights nên không đo reach. "Trang đang nguội",
    // "reach sẽ giảm" là những câu dễ bán nhất và cũng là chỗ bịa dễ nhất.
    mockBrief();
    render(<MorningBrief />);

    await screen.findByRole("button");

    const body = document.body.textContent ?? "";
    for (const claim of ["nguội", "reach", "tương tác", "thuật toán", "sẽ giảm"]) {
      expect(body).not.toContain(claim);
    }
  });

  it("không có kênh nào im lặng thì không hiện mục đó", async () => {
    // Mục trống mà vẫn hiện dạy người đọc bỏ qua nó — rồi họ bỏ qua cả lúc nó
    // có nội dung thật.
    mockBrief(brief({ silent_channels: [] }));
    render(<MorningBrief />);

    await screen.findByRole("button");

    expect(screen.queryByText(/kênh đang mở nhưng lâu chưa đăng/)).toBeNull();
  });

  it("backend chưa có field đó thì bản tin vẫn hiện, không sập", async () => {
    const { silent_channels: present, ...withoutField } = brief();
    // Chốt lại là fixture THẬT SỰ có field đó, nên bản thiếu field mới có nghĩa.
    expect(present.length).toBeGreaterThan(0);
    mockBrief(withoutField);
    render(<MorningBrief />);

    await screen.findByRole("button");

    expect(screen.getByText(/Havi đã tiết kiệm 31 phút/)).toBeInTheDocument();
  });
});
