"use client";

import { useEffect, useRef } from "react";

export interface UsePollOptions {
  /** Khoảng thời gian giữa các lần poll khi chạy bình thường (mặc định 15,000ms = 15s). */
  intervalMs?: number;
  /** Khoảng thời gian tối đa khi lỗi và áp dụng exponential backoff (mặc định 60,000ms = 60s). */
  maxIntervalMs?: number;
  /** Bật/tắt polling (mặc định true). Truyền false khi người dùng đang gõ/tương tác. */
  enabled?: boolean;
  /** Chạy ngay một nhịp khi tab được active trở lại (mặc định true). */
  immediateOnVisible?: boolean;
}

const DEFAULT_INTERVAL_MS = 15_000;
const DEFAULT_MAX_INTERVAL_MS = 60_000;

/**
 * Hook polling ngầm theo chu kỳ, nhận biết visibility của tab trình duyệt
 * và tự động backoff khi gặp lỗi mạng.
 *
 * - Chạy mỗi `intervalMs` (15s) khi tab đang active.
 * - Tạm dừng hoàn toàn khi tab bị ẩn (tiết kiệm pin & CPU cho chủ tiệm).
 * - Exponential backoff: 15s → 30s → 60s max khi callback ném lỗi / reject.
 * - Phục hồi về 15s ngay khi request thành công.
 * - Dừng poll khi `enabled === false` (ví dụ đang mở soạn tin nhắn).
 */
export function usePoll(
  fn: () => Promise<unknown> | unknown,
  options: UsePollOptions = {},
): void {
  const {
    intervalMs = DEFAULT_INTERVAL_MS,
    maxIntervalMs = DEFAULT_MAX_INTERVAL_MS,
    enabled = true,
    immediateOnVisible = true,
  } = options;

  const fnRef = useRef(fn);
  useEffect(() => {
    fnRef.current = fn;
  }, [fn]);

  const currentDelayRef = useRef(intervalMs);
  useEffect(() => {
    currentDelayRef.current = intervalMs;
  }, [intervalMs]);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    let isMounted = true;
    let timerId: ReturnType<typeof setTimeout> | null = null;
    let isExecuting = false;

    const clearActiveTimer = () => {
      if (timerId !== null) {
        clearTimeout(timerId);
        timerId = null;
      }
    };

    const scheduleNext = (delay: number) => {
      clearActiveTimer();
      if (!isMounted || !enabled) return;
      if (typeof document !== "undefined" && document.visibilityState === "hidden") {
        return;
      }
      timerId = setTimeout(() => {
        void executePoll();
      }, delay);
    };

    const executePoll = async () => {
      if (!isMounted || !enabled || isExecuting) return;
      if (typeof document !== "undefined" && document.visibilityState === "hidden") {
        return;
      }

      isExecuting = true;
      try {
        await fnRef.current();
        if (!isMounted) return;
        // Thành công: phục hồi về interval chuẩn
        currentDelayRef.current = intervalMs;
        scheduleNext(intervalMs);
      } catch {
        if (!isMounted) return;
        // Thất bại: exponential backoff (15s -> 30s -> 60s max)
        const nextDelay = Math.min(currentDelayRef.current * 2, maxIntervalMs);
        currentDelayRef.current = nextDelay;
        scheduleNext(nextDelay);
      } finally {
        isExecuting = false;
      }
    };

    // Bắt đầu lập lịch poll đầu tiên
    scheduleNext(currentDelayRef.current);

    const handleVisibilityChange = () => {
      if (typeof document === "undefined") return;
      if (document.visibilityState === "visible") {
        if (immediateOnVisible) {
          void executePoll();
        } else {
          scheduleNext(currentDelayRef.current);
        }
      } else {
        // Tab bị ẩn: dừng timer
        clearActiveTimer();
      }
    };

    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", handleVisibilityChange);
    }

    return () => {
      isMounted = false;
      clearActiveTimer();
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", handleVisibilityChange);
      }
    };
  }, [enabled, intervalMs, maxIntervalMs, immediateOnVisible]);
}
