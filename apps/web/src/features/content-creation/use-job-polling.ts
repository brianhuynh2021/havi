"use client";

import { useEffect, useRef, useState } from "react";
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
};

const IDLE: JobPollState = { status: null, job: null, error: null };

/**
 * Theo dõi một content job tới khi `drafts_ready` hoặc `failed`.
 *
 * Dùng setTimeout đệ quy chứ không setInterval: mạng chậm làm request chồng lên
 * nhau nếu interval ngắn hơn thời gian phản hồi. Cách này luôn chờ lượt trước
 * xong rồi mới hẹn lượt sau.
 */
export function useJobPolling(
  jobId: string | null,
  onReady: () => void,
): JobPollState {
  const [state, setState] = useState<JobPollState>(IDLE);

  // Giữ callback trong ref để đổi identity của nó không huỷ và khởi động lại
  // vòng poll — component cha render lại là chuyện thường.
  const onReadyRef = useRef(onReady);
  useEffect(() => {
    onReadyRef.current = onReady;
  }, [onReady]);

  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;

    async function tick() {
      if (cancelled || !jobId) return;

      const result = await getJob(jobId);
      if (cancelled) return;

      if (!result.ok) {
        setState({ status: null, job: null, error: result.message });
        return;
      }

      const job = result.data;
      setState({ status: job.status, job, error: null });

      if (job.status === "drafts_ready") {
        onReadyRef.current();
        return;
      }
      if (job.status === "failed") return;

      attempt += 1;
      if (attempt >= MAX_POLLS) {
        setState({
          status: job.status,
          job,
          error:
            "Havi viết lâu hơn thường lệ. Chị tải lại trang để xem đã xong chưa nhé.",
        });
        return;
      }
      timer = setTimeout(tick, delayFor(attempt));
    }

    tick();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobId]);

  // Không có job thì trả trạng thái rỗng ngay tại đây thay vì setState trong
  // effect: state cũ của job trước không rò ra ngoài, và tránh một nhịp render
  // thừa mỗi lần job kết thúc.
  return jobId ? state : IDLE;
}
