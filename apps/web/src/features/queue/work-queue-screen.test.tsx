import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { WorkQueueScreen } from "./work-queue-screen";
import { isOverdue, waitedFor, type WorkItem } from "./queue.api";

// Bản tin có bộ test riêng (`morning-brief.test.tsx`). Ở đây nó chỉ thêm một lời
// gọi fetch vào mọi ca kiểm thử của hàng đợi.
vi.mock("./morning-brief", () => ({ MorningBrief: () => null }));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const NOW = new Date("2026-08-26T12:00:00Z");

function minutesAgo(minutes: number): string {
  return new Date(NOW.getTime() - minutes * 60_000).toISOString();
}

function item(overrides: Partial<WorkItem> = {}): WorkItem {
  return {
    kind: "inbox",
    id: "11111111-1111-1111-1111-111111111111",
    title: "Minh Anh",
    detail: "Cho em xin bảng giá phòng cuối tuần",
    channel: "facebook",
    category: "price",
    priority: 20,
    waiting_since: minutesAgo(10),
    assigned_to_user_id: null,
    assigned_to_name: null,
    platform_url: null,
    href: "/app/inbox",
    ...overrides,
  } as WorkItem;
}

function mockApi(items: WorkItem[], meId = "user-1") {
  return vi.spyOn(globalThis, "fetch").mockImplementation(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const request = input instanceof Request ? input : new Request(String(input), init);
      const url = new URL(request.url);

      if (url.pathname.endsWith("/auth/me")) {
        return jsonResponse({ id: meId, name: "Nhân viên A", email: "a@havi.vn" });
      }
      if (request.method === "POST" && url.pathname.includes("/assign")) {
        const body = (await request.clone().json()) as { user_id: string | null };
        return jsonResponse({
          ...items[0],
          assigned_to_user_id: body.user_id,
          assigned_to_name: body.user_id ? "Nhân viên A" : null,
        });
      }
      if (url.pathname.endsWith("/queue")) {
        return jsonResponse({ items, total: items.length });
      }
      return jsonResponse([]);
    },
  );
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

describe("WorkQueueScreen — bốn nguồn, một danh sách", () => {
  it("hiện việc từ mọi nguồn trong CÙNG một danh sách", async () => {
    // Đây là ý nghĩa của sản phẩm: người trực kênh không phải đi qua bốn màn.
    mockApi([
      item({ kind: "connection", id: "c1", title: "Kênh facebook cần xác thực lại", category: null }),
      item({ kind: "inbox", id: "i1" }),
      item({ kind: "publish_failure", id: "p1", title: "Bài chưa lên được kênh", category: null }),
      item({ kind: "approval", id: "a1", title: "Bản nháp chờ duyệt", category: null }),
    ]);
    render(<WorkQueueScreen />);

    await screen.findByText("Kênh facebook cần xác thực lại");
    const rows = document.querySelectorAll("ul li");
    expect(rows).toHaveLength(4);
    expect(screen.getByText("Bài chưa lên được kênh")).toBeInTheDocument();
    expect(screen.getByText("Bản nháp chờ duyệt")).toBeInTheDocument();
  });

  it("giữ NGUYÊN thứ tự backend trả về, không tự xếp lại theo thời gian", async () => {
    // Thứ tự ưu tiên là luật nghiệp vụ và nó nằm ở backend
    // (`domain/policies/work_queue.py`). Frontend xếp lại là hai nguồn sự thật.
    mockApi([
      item({ kind: "inbox", id: "i1", detail: "Hỏi giá — mới 10 phút" }),
      item({ kind: "approval", id: "a1", detail: "Nháp — chờ 3 ngày", category: null, waiting_since: minutesAgo(60 * 24 * 3) }),
    ]);
    render(<WorkQueueScreen />);

    await screen.findByText("Hỏi giá — mới 10 phút");
    const texts = [...document.querySelectorAll("ul li")].map((el) => el.textContent ?? "");
    expect(texts[0]).toContain("Hỏi giá — mới 10 phút");
    expect(texts[1]).toContain("Nháp — chờ 3 ngày");
  });

  it("bộ lọc thu hẹp danh sách tại chỗ, không điều hướng đi đâu", async () => {
    mockApi([
      item({ kind: "inbox", id: "i1", detail: "Khách hỏi giá" }),
      item({ kind: "approval", id: "a1", detail: "Nháp chờ duyệt", category: null }),
    ]);
    render(<WorkQueueScreen />);
    await screen.findByText("Khách hỏi giá");

    fireEvent.click(screen.getByRole("button", { name: /Khách nhắn/ }));

    expect(screen.getByText("Khách hỏi giá")).toBeInTheDocument();
    expect(screen.queryByText("Nháp chờ duyệt")).toBeNull();
  });

  it("chỉ hiện nút mở nền tảng khi backend dựng được link", async () => {
    // `platform_url` là `null` nghĩa là ẩn nút. Một nút dẫn tới trang chủ tệ hơn
    // không có nút — bấm vài lần rồi người dùng bỏ qua cả lúc nó dẫn đúng.
    mockApi([
      item({ id: "i1", detail: "Bình luận có link", platform_url: "https://www.facebook.com/1_2" }),
      item({ id: "i2", detail: "Tin nhắn không link", platform_url: null }),
    ]);
    render(<WorkQueueScreen />);
    await screen.findByText("Bình luận có link");

    const links = screen.getAllByRole("link", { name: /Mở trên nền tảng/ });
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", "https://www.facebook.com/1_2");
  });

  it("nhận việc rồi bỏ nhận, và tên người nhận hiện lên", async () => {
    mockApi([item({ id: "i1" })]);
    render(<WorkQueueScreen />);

    const claim = await screen.findByRole("button", { name: /Tôi nhận/ });
    fireEvent.click(claim);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Bỏ nhận/ })).toBeInTheDocument(),
    );
  });

  it("việc người khác đang xử lý thì nói rõ, và nhận thay được", async () => {
    // Resort có nhiều nhân viên trực ca. Không nói rõ ai đang làm thì hai người
    // cùng trả lời một khách — nhưng cũng phải nhận thay được, vì hết ca nhân
    // viên về nhà và việc đã nhận sẽ kẹt vĩnh viễn.
    mockApi([
      item({ id: "i1", assigned_to_user_id: "user-2", assigned_to_name: "Nhân viên B" }),
    ]);
    render(<WorkQueueScreen />);

    expect(await screen.findByText(/Nhân viên B đang xử lý/)).toBeInTheDocument();
    // Nhãn khác "Tôi nhận" để không ai nhận thay do bấm nhầm.
    expect(screen.getByRole("button", { name: /Nhận thay/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Tôi nhận$/ })).toBeNull();
  });

  it("hết việc thì nói thẳng là hết, không hiện danh sách rỗng", async () => {
    mockApi([]);
    render(<WorkQueueScreen />);

    expect(await screen.findByText("Hết việc rồi")).toBeInTheDocument();
    expect(document.querySelectorAll("ul li")).toHaveLength(0);
  });

  it("lỗi mạng thì báo bằng tiếng Việt và cho thử lại", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fail"));
    render(<WorkQueueScreen />);

    expect(await screen.findByRole("button", { name: /Thử lại/ })).toBeInTheDocument();
  });

  it("KHÔNG hiện chỉ số kinh doanh nào", async () => {
    // Havi báo cáo việc nó đã làm; kết quả kinh doanh thuộc về doanh nghiệp.
    mockApi([item()]);
    render(<WorkQueueScreen />);
    await screen.findByText("Minh Anh");

    const body = document.body.textContent ?? "";
    for (const banned of ["Doanh thu", "doanh thu", "Đã chốt", "Khách quan tâm", "PHỄU"]) {
      expect(body).not.toContain(banned);
    }
  });
});

describe("waitedFor", () => {
  it("nói theo thời gian tương đối, vì câu hỏi là “để lâu chưa”", () => {
    expect(waitedFor(minutesAgo(0), NOW)).toBe("vừa xong");
    expect(waitedFor(minutesAgo(25), NOW)).toBe("25 phút");
    expect(waitedFor(minutesAgo(180), NOW)).toBe("3 giờ");
    expect(waitedFor(minutesAgo(60 * 48), NOW)).toBe("2 ngày");
  });

  it("không trả số âm khi đồng hồ máy chạy lệch", () => {
    const future = new Date(NOW.getTime() + 60_000).toISOString();
    expect(waitedFor(future, NOW)).toBe("vừa xong");
  });
});

describe("isOverdue", () => {
  it("ngưỡng theo mức thiệt hại, không dùng một con số chung", () => {
    // Khách hỏi giá chờ 2 giờ là lâu; một bản nháp chờ 2 giờ thì bình thường.
    expect(isOverdue(item({ category: "price", waiting_since: minutesAgo(120) }), NOW)).toBe(true);
    expect(
      isOverdue(item({ kind: "approval", category: null, waiting_since: minutesAgo(120) }), NOW),
    ).toBe(false);
  });

  it("kênh mất quyền luôn là quá hạn", () => {
    expect(
      isOverdue(item({ kind: "connection", category: null, waiting_since: minutesAgo(1) }), NOW),
    ).toBe(true);
  });

  it("tin hỏi thông tin được thoáng hơn tin hỏi giá", () => {
    const waiting = minutesAgo(90);
    expect(isOverdue(item({ category: "price", waiting_since: waiting }), NOW)).toBe(true);
    expect(isOverdue(item({ category: "info", waiting_since: waiting }), NOW)).toBe(false);
  });
});
