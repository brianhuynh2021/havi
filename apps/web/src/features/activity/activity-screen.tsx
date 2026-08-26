"use client";

/**
 * Lịch sử hoạt động — ai đã làm gì, lúc nào, và cái gì hỏng.
 *
 * Một audit log không ai đọc được thì không phải audit log. Bảng `event_log` vốn
 * dựng để support debug: mỗi dòng có `job_kind` kiểu `publish.run_job` và hai ô
 * summary chứa dữ liệu thô. Màn này **dịch sang tiếng người và bỏ phần thô** —
 * ở đó có thể là nội dung bài, id nền tảng, hay mẩu payload webhook.
 *
 * Dòng lỗi hiện nguyên văn lý do: đó là thứ duy nhất trong bảng thật sự cần
 * đọc chi tiết, và giấu nó đi thì người trực không biết phải xử lý gì.
 */

import { useLanguage } from "@/lib/i18n/language-context";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { listActivity, type ActivityEvent } from "./activity.api";
import styles from "./activity.module.css";

/**
 * `job_kind` → câu tiếng Việt. Khoá không có ở đây vẫn hiện được, dưới dạng
 * chính `job_kind` — thà hiện tên kỹ thuật còn hơn nuốt mất một dòng lịch sử.
 */
// i18n-data: nhãn việc đã xảy ra, `t()` dịch ở chỗ render
const ACTION_LABELS: Record<string, string> = {
  "content.generate_drafts": "Havi soạn bản nháp mới",
  "content.approve": "Duyệt nội dung",
  "content.reject": "Trả nội dung về để sửa",
  "content.dismiss": "Bỏ một bản nháp",
  "content.reschedule": "Đổi giờ đăng",
  "content.update": "Sửa nội dung",
  "publish.run_job": "Gửi bài lên kênh",
  "inbox.webhook_received": "Nhận tin nhắn từ khách",
  "inbox.reply_sent": "Trả lời khách",
  "connection.connected": "Nối kênh",
  "connection.disconnected": "Ngắt kênh",
  "billing.subscription_activated": "Kích hoạt gói dịch vụ",
};

function describeAction(event: ActivityEvent): string {
  return ACTION_LABELS[event.job_kind] ?? event.job_kind;
}

const timeFormatter = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function ActivityScreen() {
  const {
    t
  } = useLanguage();

  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [errorOnly, setErrorOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const result = await listActivity({ errorOnly });
    if (result.ok) {
      setEvents(result.data.items);
      setTotal(result.data.total);
      setError(null);
    } else {
      setError(result.message);
    }
    setLoading(false);
  }, [errorOnly]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("Lịch sử hoạt động")}</h1>
        <p className={styles.subtitle}>{t(
          "Mọi việc đã xảy ra trong workspace này — ai làm, lúc nào, và cái gì\n          hỏng. Dùng để đối chiếu khi có gì đó không như mong đợi."
        )}</p>
      </header>

      <div className={styles.filterRow} role="group" aria-label={t("Lọc lịch sử")}>
        <button
          type="button"
          aria-pressed={!errorOnly}
          className={`${styles.filterChip} ${!errorOnly ? styles.filterChipActive : ""}`}
          onClick={() => setErrorOnly(false)}
        >{t("Tất cả")}</button>
        <button
          type="button"
          aria-pressed={errorOnly}
          className={`${styles.filterChip} ${errorOnly ? styles.filterChipActive : ""}`}
          onClick={() => setErrorOnly(true)}
        >{t("Chỉ việc hỏng")}</button>
        {!loading && !error ? <span className={styles.countHint}>{total}{" "}{t("mục")}</span> : null}
      </div>

      {error ? (
        <ErrorState
          title={t(error)}
          action={
            <Button variant="outline" onClick={load}>{t("Thử lại")}</Button>
          }
        />
      ) : loading ? (
        <LoadingState title={t("Đang tải lịch sử…")} />
      ) : events.length === 0 ? (
        <EmptyState
          title={t(errorOnly ? "Không có việc nào hỏng" : "Chưa có hoạt động nào")}
          body={
            errorOnly
              ? "Mọi việc trong khoảng thời gian này đều chạy trót lọt."
              : "Lịch sử sẽ hiện ra khi bạn bắt đầu soạn và đăng nội dung."
          }
        />
      ) : (
        <ol className={styles.list}>
          {events.map((event) => (
            <li
              key={event.id}
              className={`${styles.row} ${event.error ? styles.rowError : ""}`}
            >
              <time className={styles.when}>
                {timeFormatter.format(new Date(event.created_at))}
              </time>
              <div className={styles.what}>
                <span className={styles.action}>{describeAction(event)}</span>
                {/* Chỉ lỗi mới hiện chi tiết. `input_summary`/`output_summary`
                    chứa dữ liệu thô không dành cho người dùng. */}
                {event.error ? <p className={styles.reason}>{event.error}</p> : null}
              </div>
              <span className={event.error ? styles.badgeError : styles.badgeOk}>
                {t(event.error ? "Hỏng" : "Xong")}
              </span>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
