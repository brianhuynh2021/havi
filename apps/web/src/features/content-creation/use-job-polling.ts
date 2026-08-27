"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useLanguage } from "@/lib/i18n/language-context";
import { getJob, type ContentJob, type JobStatus } from "./content-creation.api";

/** Poll thưa dần: draft p95 dưới 90 giây (ROADMAP §9) nên vài giây đầu đáng
 * hỏi dồn, sau đó giãn ra để không đốt pin và 4G của chủ tiệm. */
const POLL_DELAYS_MS = [1500, 2000, 3000, 4000, 5000];

/** Trần an toàn ~3 phút. Job thật quá mốc này gần như chắc chắn đã kẹt, cứ poll
 * mãi thì user nhìn spinner vô tận mà không có đường thoát. */
const MAX_POLLS = 45;
const SLOW_AFTER_MS = 20_000;

function delayFor(attempt: number): number {
  return POLL_DELAYS_MS[Math.min(attempt, POLL_DELAYS_MS.length - 1)];
}

export type JobPollState = {
  status: JobStatus | null;
  job: ContentJob | null;
  error: string | null;
  slow: boolean;
  activeCount: number;
  addJobId: (id: string) => void;
  resetJob: () => void;
};

/**
 * Theo dõi các content job đang chạy ngầm tới khi `drafts_ready` hoặc `failed`.
 *
 * Hỗ trợ chạy nhiều job cùng lúc không chắn giao diện (Async non-blocking queue).
 */
export function useJobPolling(
  initialJobId: string | null,
  onReady: () => void,
  options: { maxPolls?: number; slowAfterMs?: number } = {},
): JobPollState {
  const { t } = useLanguage();
  const [jobIds, setJobIds] = useState<string[]>(() => (initialJobId ? [initialJobId] : []));
  const [prevInitialJobId, setPrevInitialJobId] = useState<string | null>(initialJobId);
  const maxPolls = options.maxPolls ?? MAX_POLLS;
  const slowAfterMs = options.slowAfterMs ?? SLOW_AFTER_MS;
  const [state, setState] = useState<{
    status: JobStatus | null;
    job: ContentJob | null;
    error: string | null;
    slow: boolean;
  }>({ status: null, job: null, error: null, slow: false });

  // Cập nhật jobIds khi prop initialJobId thay đổi
  if (initialJobId !== prevInitialJobId) {
    setPrevInitialJobId(initialJobId);
    if (initialJobId && !jobIds.includes(initialJobId)) {
      setJobIds((prev) => [...prev, initialJobId]);
    }
  }

  const onReadyRef = useRef(onReady);
  useEffect(() => {
    onReadyRef.current = onReady;
  }, [onReady]);

  const addJobId = useCallback((id: string) => {
    setJobIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
  }, []);

  const resetJob = useCallback(() => {
    setJobIds([]);
    setState({ status: null, job: null, error: null, slow: false });
  }, []);

  // P1 vận hành: sau 20 giây người dùng phải biết job vẫn đang chạy, không phải
  // đoán spinner đã treo. Timer này chỉ đổi copy; worker vẫn tiếp tục và kết quả
  // vẫn được poll bình thường.
  useEffect(() => {
    if (!jobIds.length) {
      setState((current) => (current.slow ? { ...current, slow: false } : current));
      return;
    }
    const timer = setTimeout(() => {
      setState((current) => ({ ...current, slow: true }));
    }, slowAfterMs);
    return () => clearTimeout(timer);
  }, [jobIds.length, slowAfterMs]);

  useEffect(() => {
    if (!jobIds.length) {
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;

    async function tick() {
      if (cancelled || !jobIds.length) return;

      const remaining: string[] = [];
      let anyReady = false;
      let lastError: string | null = null;
      let lastStatus: JobStatus | null = null;
      let lastJob: ContentJob | null = null;

      for (const id of jobIds) {
        const result = await getJob(id);
        if (cancelled) return;

        if (!result.ok) {
          lastError = result.message;
          // Lỗi đọc trạng thái có thể chỉ là một nhịp mạng yếu. Bỏ id ở đây làm
          // frontend ngừng theo dõi một job vẫn đang chạy và không bao giờ báo
          // khi bản nháp sẵn sàng.
          remaining.push(id);
          continue;
        }

        const job = result.data;
        lastStatus = job.status;
        lastJob = job;

        if (job.status === "drafts_ready") {
          anyReady = true;
        } else if (job.status === "failed") {
          lastStatus = "failed";
          lastError = t(
            "Havi chưa viết được bài này. Bạn có thể kiểm tra nội dung rồi bấm tạo lại.",
          );
        } else {
          remaining.push(id);
        }
      }

      if (anyReady) {
        onReadyRef.current();
      }

      setState((current) => ({
        status: lastStatus,
        job: lastJob,
        error: lastError,
        slow: remaining.length > 0 && current.slow,
      }));

      if (cancelled) return;
      // Không tạo mảng state mới khi danh sách không đổi. Trước đây mỗi poll
      // làm effect chạy lại, `attempt` về 0 và trần MAX_POLLS không bao giờ tới.
      setJobIds((current) =>
        current.length === remaining.length &&
        current.every((id, index) => id === remaining[index])
          ? current
          : remaining,
      );

      if (remaining.length > 0) {
        attempt += 1;
        if (attempt >= maxPolls) {
          setState({
            status: null,
            job: lastJob,
            error: t("Havi viết lâu hơn thường lệ. Bạn tải lại trang để xem đã xong chưa nhé."),
            slow: false,
          });
          setJobIds([]);
          return;
        }
        timer = setTimeout(tick, delayFor(attempt));
      }
    }

    tick();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobIds, maxPolls, t]);

  return {
    status: state.status,
    job: state.job,
    error: state.error,
    slow: state.slow,
    activeCount: jobIds.length,
    addJobId,
    resetJob,
  };
}
