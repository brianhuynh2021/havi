"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { channelLabels } from "@/features/content-creation/content-creation.fixture";
import { FailedPostsPanel } from "@/features/publish-jobs/failed-posts-panel";
import {
  addDays,
  fetchCalendar,
  startOfVnWeek,
  toVnDateString,
  type CalendarDay,
} from "./calendar.api";
import { statusLabel, statusTone, weekdayLabels } from "./calendar.fixture";
import styles from "./calendar.module.css";

/** Giờ đăng hiện theo giờ VN, không theo giờ máy — chủ tiệm ở VN và backend
 * cũng gom nhóm theo múi giờ đó. Máy đặt lệch múi giờ vẫn phải thấy đúng giờ. */
const vnTime = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function dayLabel(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${day}/${month}`;
}

export function CalendarScreen() {
  const [weekStart, setWeekStart] = useState(() => startOfVnWeek(new Date()));
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const today = toVnDateString(new Date());

  // `reloadKey` để nút "Thử lại" nạp lại đúng tuần đang xem mà không phải nhân
  // đôi logic fetch ra ngoài effect.
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      const result = await fetchCalendar(
        toVnDateString(weekStart),
        toVnDateString(addDays(weekStart, 6)),
      );
      if (cancelled) return;
      if (result.ok) {
        setDays(result.data);
        setError(null);
      } else {
        setError(result.message);
      }
      setLoading(false);
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [weekStart, reloadKey]);

  const empty = days.every((day) => day.items.length === 0);
  const rangeLabel = days.length
    ? `${dayLabel(days[0].date)} – ${dayLabel(days[days.length - 1].date)}`
    : "";

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>Lịch đăng</h1>
        <p className={styles.subtitle}>
          Bài đã duyệt tự xếp vào đúng ngày/giờ — múi giờ Asia/Ho_Chi_Minh.
        </p>
      </header>

      {/* Trên thanh chọn tuần: bài không đăng được là việc gấp hơn xem lịch, và
          nó không thuộc tuần nào cả — bài lỗi từ tuần trước vẫn phải thấy khi
          đang xem tuần này. Đăng lại xong thì nạp lại lịch để bài hiện đúng. */}
      <FailedPostsPanel onPublished={() => setReloadKey((k) => k + 1)} />

      <div className={styles.weekBar}>
        <Button
          variant="outline"
          onClick={() => setWeekStart((w) => addDays(w, -7))}
        >
          ← Tuần trước
        </Button>
        <span className={styles.weekRange}>{rangeLabel}</span>
        <div className={styles.weekActions}>
          <Button
            variant="outline"
            onClick={() => setWeekStart(startOfVnWeek(new Date()))}
          >
            Tuần này
          </Button>
          <Button
            variant="outline"
            onClick={() => setWeekStart((w) => addDays(w, 7))}
          >
            Tuần sau →
          </Button>
        </div>
      </div>

      {error ? (
        <ErrorState
          title={error}
          action={
            <Button variant="outline" onClick={() => setReloadKey((k) => k + 1)}>
              Thử lại
            </Button>
          }
        />
      ) : loading ? (
        <LoadingState title="Đang tải lịch…" />
      ) : (
        <>
          <section className={styles.grid} aria-label="Lịch đăng theo tuần">
            {days.map((day, index) => (
              <div
                key={day.date}
                className={`${styles.dayColumn} ${
                  day.date === today ? styles.dayColumnToday : ""
                }`}
              >
                <div className={styles.dayHeader}>
                  <span className={styles.dayLabel}>{weekdayLabels[index]}</span>
                  <span className={styles.dayDate}>{dayLabel(day.date)}</span>
                </div>

                {day.items.length === 0 ? (
                  <p className={styles.dayEmpty}>Chưa có bài</p>
                ) : (
                  <div className={styles.postList}>
                    {day.items.map((item) => (
                      <article key={item.id} className={styles.postCard}>
                        <div className={styles.postMeta}>
                          <span className={styles.postTime}>
                            {item.scheduled_at
                              ? vnTime.format(new Date(item.scheduled_at))
                              : "--:--"}
                          </span>
                          <span className={styles.postChannel}>
                            {channelLabels[
                              item.channel as keyof typeof channelLabels
                            ] ?? item.channel}
                          </span>
                        </div>
                        <p className={styles.postExcerpt}>{item.text}</p>
                        <Badge tone={statusTone[item.status]}>
                          {statusLabel[item.status]}
                        </Badge>
                      </article>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </section>

          {empty ? (
            <EmptyState
              title="Chưa có bài nào được lên lịch tuần này"
              body="Duyệt một bản nháp ở tab Tạo nội dung để thấy bài xuất hiện ở đây."
            />
          ) : null}
        </>
      )}
    </>
  );
}
