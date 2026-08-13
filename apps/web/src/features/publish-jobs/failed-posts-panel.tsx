"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { channelLabels } from "@/features/content-creation/content-creation.fixture";
import {
  failureCopy,
  listDeadLetterJobs,
  retryPublishJob,
  type PublishJob,
} from "./publish-jobs.api";
import styles from "./failed-posts-panel.module.css";

const vnDateTime = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

type Props = {
  /** Gọi sau khi một bài đăng lại thành công, để màn ngoài nạp lại lịch. */
  onPublished?: () => void;
};

/**
 * Danh sách bài đã dừng hẳn sau nhiều lần đăng lỗi, kèm nút "Thử lại".
 *
 * Không có màn này thì bài lỗi *biến mất trong im lặng*: backend đánh
 * `dead_letter`, ngừng thử lại, và chủ tiệm chỉ thấy bài không lên Trang mà
 * không biết vì sao — cũng không có cách nào tự xử lý ngoài gọi API bằng tay.
 *
 * Ẩn hoàn toàn khi không có bài lỗi: một khối "Không có bài lỗi" thường trực chỉ
 * làm nhiễu màn hình mà chẳng nói thêm gì.
 */
export function FailedPostsPanel({ onPublished }: Props) {
  const [jobs, setJobs] = useState<PublishJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const result = await listDeadLetterJobs();
      if (cancelled) return;
      if (result.ok) {
        setJobs(result.data);
        // KHÔNG xoá `error` ở đây. Việc nạp lại thường được kích hoạt *bởi* một
        // lỗi (409 → nạp lại cho khớp backend), nên xoá lỗi trong lượt nạp đó
        // thổi bay đúng thông báo vừa đặt: chủ tiệm bấm nút, không thấy gì xảy
        // ra, và không hiểu vì sao.
        return;
      }
      setError(result.message);
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  async function retry(job: PublishJob) {
    setBusyId(job.id);
    setError(null);
    const result = await retryPublishJob(job.id);
    setBusyId(null);

    if (!result.ok) {
      setError(result.message);
      // 409 nghĩa là trạng thái đã đổi ở nơi khác — nạp lại để danh sách khớp
      // backend, thay vì để chủ tiệm bấm mãi một nút không còn hợp lệ.
      setReloadKey((k) => k + 1);
      return;
    }

    if (result.data.status === "succeeded") {
      setJobs((current) => current.filter((j) => j.id !== job.id));
      onPublished?.();
      return;
    }

    // Thử lại vẫn hỏng: thay bản ghi bằng bản mới để chủ tiệm thấy lý do lần
    // này, không phải lý do lần trước.
    setJobs((current) =>
      current.map((j) => (j.id === job.id ? result.data : j)),
    );
  }

  if (jobs.length === 0 && !error) return null;

  return (
    <section className={styles.panel} aria-label="Bài đăng chưa thành công">
      <header className={styles.header}>
        <h2 className={styles.title}>
          {jobs.length > 0
            ? `${jobs.length} bài chưa đăng được`
            : "Bài chưa đăng được"}
        </h2>
        <p className={styles.subtitle}>
          Havi đã thử vài lần rồi dừng để không đăng trùng. Chị xem lý do rồi
          quyết định giúp em nhé.
        </p>
      </header>

      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}

      <ul className={styles.list}>
        {jobs.map((job) => {
          const copy = failureCopy(job.failure_kind);
          return (
            <li key={job.id} className={styles.item}>
              <div className={styles.itemHead}>
                <Badge tone="warning">{copy.title}</Badge>
                <span className={styles.channel}>
                  {channelLabels[job.channel as keyof typeof channelLabels] ??
                    job.channel}
                </span>
                <span className={styles.when}>
                  Lịch đăng {vnDateTime.format(new Date(job.scheduled_at))}
                </span>
              </div>

              <p className={styles.hint}>{copy.hint}</p>

              {/* Chi tiết lỗi từ nền tảng — để support tra được mà không cần
                  đọc log server. Đặt trong <details> vì chủ tiệm không cần đọc
                  nó trong luồng bình thường. */}
              {job.failure_detail ? (
                <details className={styles.details}>
                  <summary className={styles.summary}>Chi tiết lỗi</summary>
                  <p className={styles.detailText}>{job.failure_detail}</p>
                </details>
              ) : null}

              <div className={styles.actions}>
                {copy.canRetry ? (
                  <Button
                    variant="primary"
                    onClick={() => retry(job)}
                    disabled={busyId === job.id}
                  >
                    {busyId === job.id ? "Đang đăng lại…" : "Thử lại"}
                  </Button>
                ) : null}
                {copy.needsReconnect ? (
                  <Link className={styles.reconnect} href="/app/settings">
                    Nối lại kênh
                  </Link>
                ) : null}
                <span className={styles.attempts}>
                  Đã thử {job.attempt_count} lần
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
