import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { writeTokens } from "@/lib/auth/token-store";
import { CalendarScreen } from "./calendar-screen";
import { startOfVnWeek, toVnDateString } from "./calendar.api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function emptyWeek(startIso: string) {
  const start = new Date(`${startIso}T00:00:00Z`);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setUTCDate(d.getUTCDate() + i);
    return { date: d.toISOString().slice(0, 10), items: [] };
  });
}

function item(overrides: Record<string, unknown> = {}) {
  return {
    id: "c1",
    workspace_id: "w1",
    job_id: null,
    channel: "facebook_page",
    kind: "Bài ảnh",
    text: "Ưu đãi gội đầu thảo dược cuối tuần",
    status: "scheduled",
    version_no: 1,
    ...overrides,
  };
}

/** Trả về mọi `start`/`end` mà màn đã hỏi, để verify khoảng ngày gửi lên.
 *
 * Route theo URL chứ không trả cùng một body cho mọi lời gọi: màn Lịch đăng còn
 * gắn `FailedPostsPanel`, panel đó gọi `/content/publish-jobs`. Ghi cả lời gọi
 * đó vào `asked` thì `asked[0]` không còn chắc là request lịch nữa. */
function mockCalendar(
  daysFor: (start: string) => unknown[],
  deadLetterJobs: unknown[] = [],
  onReschedule?: (body: unknown) => Response,
) {
  const asked: { start: string; end: string }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(
    async (input: RequestInfo | URL) => {
      const request = input instanceof Request ? input : new Request(input);
      const url = new URL(request.url);
      if (url.pathname.includes("/publish-jobs")) {
        return jsonResponse(deadLetterJobs);
      }
      if (request.method === "POST" && url.pathname.includes("/reschedule")) {
        return onReschedule?.(await request.json()) ?? jsonResponse(item());
      }
      const start = url.searchParams.get("start") ?? "";
      const end = url.searchParams.get("end") ?? "";
      asked.push({ start, end });
      return jsonResponse({ days: daysFor(start) });
    },
  );
  return asked;
}

describe("CalendarScreen", () => {
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

  it("hỏi đúng 7 ngày từ thứ Hai theo giờ VN", async () => {
    const asked = mockCalendar((start) => emptyWeek(start));
    render(<CalendarScreen />);

    await waitFor(() => expect(asked.length).toBeGreaterThan(0));
    const monday = toVnDateString(startOfVnWeek(new Date()));
    expect(asked[0].start).toBe(monday);

    const days =
      (new Date(`${asked[0].end}T00:00:00Z`).getTime() -
        new Date(`${asked[0].start}T00:00:00Z`).getTime()) /
      86_400_000;
    expect(days).toBe(6); // inclusive hai đầu → 7 ngày
  });

  it("workspace mới thì báo chưa có bài, không render số liệu giả", async () => {
    mockCalendar((start) => emptyWeek(start));
    render(<CalendarScreen />);

    expect(
      await screen.findByText(/chưa có bài nào được lên lịch/i),
    ).toBeInTheDocument();
  });

  it("hiện bài thật kèm nhãn kênh và trạng thái tiếng Việt", async () => {
    mockCalendar((start) => {
      const days = emptyWeek(start) as { date: string; items: unknown[] }[];
      days[0].items = [
        item({ scheduled_at: `${days[0].date}T02:30:00Z` }),
        item({ id: "c2", channel: "zalo_oa", status: "published", text: "Bài Zalo" }),
      ];
      return days;
    });
    render(<CalendarScreen />);

    expect(
      await screen.findByText("Ưu đãi gội đầu thảo dược cuối tuần"),
    ).toBeInTheDocument();
    expect(screen.getByText("Zalo OA")).toBeInTheDocument();
    expect(screen.getByText("Đã lên lịch")).toBeInTheDocument();
    expect(screen.getAllByText("Đã đăng").length).toBeGreaterThanOrEqual(1);
  });

  it("giờ hiện theo múi giờ VN, không theo UTC", async () => {
    // 02:30 UTC = 09:30 giờ VN. Hiện 02:30 là đã quên +07.
    mockCalendar((start) => {
      const days = emptyWeek(start) as { date: string; items: unknown[] }[];
      days[0].items = [item({ scheduled_at: `${days[0].date}T02:30:00Z` })];
      return days;
    });
    render(<CalendarScreen />);

    expect(await screen.findByText("09:30")).toBeInTheDocument();
    expect(screen.queryByText("02:30")).not.toBeInTheDocument();
  });

  it("bấm Sau ở chế độ tuần thì hỏi đúng tuần kế tiếp", async () => {
    const asked = mockCalendar((start) => emptyWeek(start));
    render(<CalendarScreen />);
    await waitFor(() => expect(asked.length).toBe(1));

    const user = userEvent.setup();
    // Nút lùi/tiến dùng chung cho cả chế độ tuần và tháng nên nhãn chỉ là
    // "Trước"/"Sau"; bước nhảy do `viewMode` quyết định — mặc định là tuần.
    await user.click(screen.getByRole("button", { name: /Sau/ }));

    await waitFor(() => expect(asked.length).toBe(2));
    const diff =
      (new Date(`${asked[1].start}T00:00:00Z`).getTime() -
        new Date(`${asked[0].start}T00:00:00Z`).getTime()) /
      86_400_000;
    expect(diff).toBe(7);
  });

  it("lỗi mạng thì báo bằng tiếng Việt và cho thử lại", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fail"));
    render(<CalendarScreen />);

    // Mất mạng thì cả lịch và FailedPostsPanel đều báo lỗi — đúng, vì cả hai đều
    // hỏng thật. Nên tìm theo nội dung thay vì giả định chỉ có một alert.
    const alerts = await screen.findAllByRole("alert");
    expect(
      alerts.some((el) => /không kết nối được/i.test(el.textContent ?? "")),
    ).toBe(true);
    expect(
      screen.getByRole("button", { name: /thử lại/i }),
    ).toBeInTheDocument();
  });

  it("có bài đăng lỗi thì hiện panel ngay trên lịch", async () => {
    mockCalendar((start) => emptyWeek(start), [
      {
        id: "job-1",
        workspace_id: "w1",
        content_item_id: "c1",
        channel: "facebook_page",
        status: "dead_letter",
        scheduled_at: "2026-08-09T13:00:00Z",
        attempt_count: 4,
        next_attempt_at: null,
        external_post_id: null,
        published_at: null,
        failure_kind: "temporary",
        failure_detail: "Rate limit",
      },
    ]);
    render(<CalendarScreen />);

    // Bài lỗi không thuộc tuần nào — phải thấy được kể cả khi đang xem tuần khác.
    expect(await screen.findByText(/1 bài chưa đăng được/)).toBeInTheDocument();
  });

  it("đổi ngày giờ đăng bằng timezone VN và nạp lại lịch sau khi lưu", async () => {
    const bodies: unknown[] = [];
    const asked = mockCalendar(
      (start) => {
        const days = emptyWeek(start) as { date: string; items: unknown[] }[];
        days[0].items = [item({ scheduled_at: `${days[0].date}T02:30:00Z` })];
        return days;
      },
      [],
      (body) => {
        bodies.push(body);
        return jsonResponse(item({ scheduled_at: "2026-08-11T03:15:00Z" }));
      },
    );
    render(<CalendarScreen />);

    const user = userEvent.setup();
    await user.click(await screen.findByText(/Ưu đãi gội đầu thảo dược/i));
    await user.clear(screen.getByLabelText("Giờ đăng mới"));
    await user.type(screen.getByLabelText("Giờ đăng mới"), "2026-08-11T10:15");
    await user.click(screen.getByRole("button", { name: "Lưu giờ mới" }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toEqual({ scheduled_at: "2026-08-11T10:15:00+07:00" });
    await waitFor(() => expect(asked.length).toBeGreaterThan(1));
  });

  it("backend từ chối 409 thì báo lỗi và nạp lại lịch", async () => {
    const asked = mockCalendar(
      (start) => {
        const days = emptyWeek(start) as { date: string; items: unknown[] }[];
        days[0].items = [item()];
        return days;
      },
      [],
      () => jsonResponse({ detail: "published" }, 409),
    );
    render(<CalendarScreen />);

    const user = userEvent.setup();
    await user.click(await screen.findByText(/Ưu đãi gội đầu thảo dược/i));
    await user.click(screen.getByRole("button", { name: "Lưu giờ mới" }));

    expect(
      await screen.findByText(/đã đăng rồi nên không đổi lịch được nữa/i),
    ).toBeInTheDocument();
    await waitFor(() => expect(asked.length).toBeGreaterThan(1));
  });
});
