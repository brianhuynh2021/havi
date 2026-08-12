"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getJob, type ContentJob, type JobStatus } from "./content-creation.api";

/** Poll thưa dần: draft p95 dưới 90 giây (ROADMAP §9) nên vài giây đầu đáng
 * hỏi dồn, sau đó giãn ra để không đốt pin và 4G của chủ tiệm. */
const POLL_DELAYS_MS = [1500, 2000, 3000, 4000, 5000];

/** Trần an toàn ~3 phút. Job thật quá mốc này gần như chắc chắn đã kẹt, cứ poll
 * mãi thì user nhìn spinner vô tận mà không có đường thoát. */
const MAX_POLLS = 45;

function delayFor(attempt: number): number {
  return POLL_DELAYS_MS[Math.min(attempt, POLL_DELAYS_MS.length - 1)];
}

export type JobPollState = {
  status: JobStatus | null;
  job: ContentJob | null;
  error: string | null;
  activeCount: number;
  addJobId: (id: string) => void;
  resetJob: () => void;
};

const IDLE: JobPollState = {
  status: null,
  job: null,
  error: null,
  activeCount: 0,
  addJobId: () => {},
  resetJob: () => {},
};

/**
  * Theo dõi các content job đang chạy ngầm tới khi `drafts_ready` hoặc `failed`.
  *
  * Hỗ trợ chạy nhiều job cùng lúc không chắn giao diện (Async non-blocking queue).
  */
export function useJobPolling(
  initialJobId: string | null,
  onReady: () => void,
): JobPollState {
  const [jobIds, setJobIds] = useState<string[]>([]);
  const [state, setState] = useState<{
    status: JobStatus | null;
    job: ContentJob | null;
    error: string | null;
  }>({ status: null, job: null, error: null });

  // Cập nhật jobIds khi prop initialJobId thay đổi
  useEffect(() => {
    if (initialJobId) {
      setJobIds((prev) => (prev.includes(initialJobId) ? prev : [...prev, initialJobId]));
    }
  }, [initialJobId]);

  const onReadyRef = useRef(onReady);
  useEffect(() => {
    onReadyRef.current = onReady;
  }, [onReady]);

  const addJobId = useCallback((id: string) => {
    setJobIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
  }, []);

  const resetJob = useCallback(() => {
    setJobIds([]);
    setState({ status: null, job: null, error: null });
  }, []);

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
          continue;
        }

        const job = result.data;
        lastStatus = job.status;
        lastJob = job;

        if (job.status === "drafts_ready") {
          anyReady = true;
        } else if (job.status === "failed") {
          lastStatus = "failed";
        } else {
          remaining.push(id);
        }
      }

      if (anyReady) {
        onReadyRef.current();
      }

      setState({
        status: lastStatus,
        job: lastJob,
        error: lastError,
      });

      if (cancelled) return;
      setJobIds(remaining);

      if (remaining.length > 0) {
        attempt += 1;
        if (attempt >= MAX_POLLS) {
          setState({
            status: lastStatus,
            job: lastJob,
            error: "Havi viết lâu hơn thường lệ. Chị tải lại trang để xem đã xong chưa nhé.",
          });
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
  }, [jobIds]);

  return {
    status: state.status,
    job: state.job,
    error: state.error,
    activeCount: jobIds.length,
    addJobId,
    resetJob,
  };
}
