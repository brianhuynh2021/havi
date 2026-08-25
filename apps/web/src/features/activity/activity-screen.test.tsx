import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ActivityScreen } from "./activity-screen";

const listActivity = vi.fn();

vi.mock("./activity.api", () => ({
  listActivity: (...args: unknown[]) => listActivity(...args),
}));

function event(overrides: Record<string, unknown> = {}) {
  return {
    id: `e-${Math.random()}`,
    workspace_id: "w1",
    job_id: null,
    request_id: null,
    job_kind: "publish.run_job",
    input_summary: "raw payload không được lộ ra UI",
    output_summary: "external id không được lộ ra UI",
    tokens_in: 0,
    tokens_out: 0,
    provider: "facebook",
    duration_ms: 120,
    error: null,
    created_at: "2026-08-25T03:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  listActivity.mockResolvedValue({ ok: true, data: { items: [], total: 0 } });
});

describe("ActivityScreen — lịch sử hoạt động", () => {
  it("dịch job_kind sang tiếng người, KHÔNG lộ dữ liệu thô", async () => {
    listActivity.mockResolvedValue({
      ok: true,
      data: { items: [event()], total: 1 },
    });

    render(<ActivityScreen />);
    expect(await screen.findByText("Gửi bài lên kênh")).toBeInTheDocument();

    const body = document.body.textContent ?? "";
    expect(body).not.toContain("publish.run_job");
    expect(body).not.toContain("raw payload");
    expect(body).not.toContain("external id");
  });

  it("job_kind lạ vẫn hiện, không nuốt mất dòng lịch sử", async () => {
    listActivity.mockResolvedValue({
      ok: true,
      data: { items: [event({ job_kind: "something.brand_new" })], total: 1 },
    });

    render(<ActivityScreen />);
    // Thà hiện tên kỹ thuật còn hơn giấu một dòng lịch sử.
    expect(await screen.findByText("something.brand_new")).toBeInTheDocument();
  });

  it("dòng hỏng hiện nguyên văn lý do — đó là thứ cần đọc", async () => {
    listActivity.mockResolvedValue({
      ok: true,
      data: {
        items: [event({ error: "Facebook từ chối: token hết hạn" })],
        total: 1,
      },
    });

    render(<ActivityScreen />);
    expect(await screen.findByText(/token hết hạn/)).toBeInTheDocument();
    expect(screen.getByText("Hỏng")).toBeInTheDocument();
  });

  it("lọc chỉ việc hỏng thì gọi lại API với error_only", async () => {
    render(<ActivityScreen />);
    await waitFor(() => expect(listActivity).toHaveBeenCalled());

    await userEvent.click(screen.getByRole("button", { name: "Chỉ việc hỏng" }));

    await waitFor(() =>
      expect(listActivity).toHaveBeenLastCalledWith({ errorOnly: true }),
    );
  });

  it("vai không có quyền thì nói thẳng, KHÔNG hiện danh sách rỗng", async () => {
    // Rỗng trông như "chưa có hoạt động nào" — sai hẳn ý nghĩa của 403.
    listActivity.mockResolvedValue({
      ok: false,
      message: "Vai của bạn không xem được lịch sử hoạt động. Cần vai Người duyệt hoặc Chủ workspace.",
    });

    render(<ActivityScreen />);
    expect(await screen.findByText(/Cần vai Người duyệt/)).toBeInTheDocument();
    expect(screen.queryByText(/Chưa có hoạt động nào/)).toBeNull();
  });

  it("không có việc hỏng nào thì nói rõ là không hỏng, không phải chưa có gì", async () => {
    render(<ActivityScreen />);
    await userEvent.click(await screen.findByRole("button", { name: "Chỉ việc hỏng" }));

    expect(await screen.findByText("Không có việc nào hỏng")).toBeInTheDocument();
  });
});
