import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useJobPolling } from "./use-job-polling";

const getJob = vi.fn();

vi.mock("./content-creation.api", () => ({
  getJob: (...args: unknown[]) => getJob(...args),
}));

function job(status: "queued" | "processing" | "drafts_ready" | "failed") {
  return {
    id: "job-1",
    workspace_id: "workspace-1",
    status,
    raw_inputs: [{ kind: "text", text: "Bài cuối tuần" }],
    content_item_ids: [],
    created_at: "2026-08-27T00:00:00Z",
  };
}

describe("useJobPolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    getJob.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("không bỏ mất job chỉ vì một nhịp đọc trạng thái lỗi mạng", async () => {
    getJob
      .mockResolvedValueOnce({ ok: false, message: "Mạng chập chờn" })
      .mockResolvedValueOnce({ ok: true, data: job("drafts_ready") });
    const onReady = vi.fn();
    const { result } = renderHook(() => useJobPolling("job-1", onReady));

    await act(async () => vi.advanceTimersByTimeAsync(0));
    expect(result.current.activeCount).toBe(1);

    await act(async () => vi.advanceTimersByTimeAsync(2_000));
    expect(onReady).toHaveBeenCalledTimes(1);
    expect(result.current.activeCount).toBe(0);
  });

  it("báo chậm sau 20 giây nhưng vẫn tiếp tục theo dõi", async () => {
    getJob.mockResolvedValue({ ok: true, data: job("processing") });
    const { result } = renderHook(() =>
      useJobPolling("job-1", vi.fn(), { slowAfterMs: 20 }),
    );

    await act(async () => vi.advanceTimersByTimeAsync(20));

    expect(result.current.slow).toBe(true);
    expect(result.current.activeCount).toBe(1);
  });

  it("job failed dừng spinner và trả thông báo có đường tạo lại", async () => {
    getJob.mockResolvedValue({ ok: true, data: job("failed") });
    const { result } = renderHook(() => useJobPolling("job-1", vi.fn()));

    await act(async () => vi.advanceTimersByTimeAsync(0));

    expect(result.current.activeCount).toBe(0);
    expect(result.current.status).toBe("failed");
    expect(result.current.error).toMatch(/bấm tạo lại/i);
  });

  it("job kẹt vượt trần thì dừng poll và mở lại nút tạo bài", async () => {
    getJob.mockResolvedValue({ ok: true, data: job("processing") });
    const { result } = renderHook(() =>
      useJobPolling("job-1", vi.fn(), { maxPolls: 3, slowAfterMs: 20 }),
    );

    await act(async () => vi.advanceTimersByTimeAsync(10_000));

    expect(result.current.activeCount).toBe(0);
    expect(result.current.status).toBeNull();
    expect(result.current.error).toMatch(/lâu hơn thường lệ/i);
  });
});
