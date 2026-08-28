import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { usePoll } from "./use-poll";

describe("usePoll", () => {
  let visibilityState = "visible";

  beforeEach(() => {
    vi.useFakeTimers();
    visibilityState = "visible";
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => visibilityState,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("chạy poll theo chu kỳ intervalMs khi tab đang active", async () => {
    const fn = vi.fn().mockResolvedValue(undefined);
    renderHook(() => usePoll(fn, { intervalMs: 15_000 }));

    expect(fn).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });
    expect(fn).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("tạm dừng poll khi tab bị ẩn và kích hoạt ngay khi tab mở lại", async () => {
    const fn = vi.fn().mockResolvedValue(undefined);
    renderHook(() => usePoll(fn, { intervalMs: 15_000, immediateOnVisible: true }));

    // Tab bị ẩn
    visibilityState = "hidden";
    document.dispatchEvent(new Event("visibilitychange"));

    // Tiến thời gian khi đang ẩn — không được gọi
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(fn).not.toHaveBeenCalled();

    // Tab quay trở lại visible — gọi ngay lập tức
    visibilityState = "visible";
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("áp dụng exponential backoff khi callback ném lỗi và phục hồi khi thành công", async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new Error("Lỗi mạng 1"))
      .mockRejectedValueOnce(new Error("Lỗi mạng 2"))
      .mockResolvedValue("Thành công");

    renderHook(() =>
      usePoll(fn, { intervalMs: 15_000, maxIntervalMs: 60_000 }),
    );

    // Lần 1: Sau 15s, chạy và fail (lần tiếp theo sẽ là 30s)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });
    expect(fn).toHaveBeenCalledTimes(1);

    // Sau 15s nữa (tổng 30s) — chưa chạy vì delay lúc này là 30s
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });
    expect(fn).toHaveBeenCalledTimes(1);

    // Sau thêm 15s nữa (đủ 30s từ lần 1) — chạy lần 2 và fail (lần tiếp theo sẽ là 60s)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });
    expect(fn).toHaveBeenCalledTimes(2);

    // Sau 60s — chạy lần 3 và thành công (lần tiếp theo phục hồi về 15s)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(fn).toHaveBeenCalledTimes(3);

    // Sau 15s từ lần 3 — chạy tiếp nhịp 15s bình thường
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });
    expect(fn).toHaveBeenCalledTimes(4);
  });

  it("không poll khi enabled = false", async () => {
    const fn = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(
      ({ enabled }) => usePoll(fn, { intervalMs: 15_000, enabled }),
      { initialProps: { enabled: false } },
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(fn).not.toHaveBeenCalled();

    // Bật lại enabled = true
    rerender({ enabled: true });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("dọn dẹp timer và listener khi unmount", async () => {
    const fn = vi.fn().mockResolvedValue(undefined);
    const { unmount } = renderHook(() =>
      usePoll(fn, { intervalMs: 15_000 }),
    );

    unmount();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(fn).not.toHaveBeenCalled();
  });
});
