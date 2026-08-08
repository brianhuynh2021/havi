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

/** Trả về mọi `start`/`end` mà màn đã hỏi, để verify khoảng ngày gửi lên. */
function mockCalendar(daysFor: (start: string) => unknown[]) {
  const asked: { start: string; end: string }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(
    async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
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
    expect(screen.getByText("Đã đăng")).toBeInTheDocument();
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

  it("bấm tuần sau thì hỏi đúng tuần kế tiếp", async () => {
    const asked = mockCalendar((start) => emptyWeek(start));
    render(<CalendarScreen />);
    await waitFor(() => expect(asked.length).toBe(1));

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /tuần sau/i }));

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

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /không kết nối được/i,
    );
    expect(screen.getByRole("button", { name: /thử lại/i })).toBeInTheDocument();
  });
});
