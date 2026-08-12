"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { channelLabels } from "@/features/content-creation/content-creation.fixture";
import { FailedPostsPanel } from "@/features/publish-jobs/failed-posts-panel";
import {
  addDays,
  fetchCalendar,
  rescheduleItem,
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

function getTopicImage(mediaNote?: string | null, text?: string | null): string {
  const combined = `${mediaNote || ""} ${text || ""}`.toLowerCase();
  if (
    combined.includes("quà") ||
    combined.includes("gift") ||
    combined.includes("thưởng") ||
    combined.includes("khuyến mãi") ||
    combined.includes("ưu đãi") ||
    combined.includes("bốc thăm") ||
    combined.includes("voucher") ||
    combined.includes("trò chơi") ||
    combined.includes("game")
  ) {
    return "https://images.unsplash.com/photo-1513151233558-d860c5398176?w=1200&q=80";
  }
  if (
    combined.includes("tóc") ||
    combined.includes("hair") ||
    combined.includes("gội") ||
    combined.includes("cắt") ||
    combined.includes("uốn") ||
    combined.includes("nhuộm")
  ) {
    return "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1200&q=80";
  }
  if (
    combined.includes("cafe") ||
    combined.includes("cà phê") ||
    combined.includes("ăn") ||
    combined.includes("uống")
  ) {
    return "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1200&q=80";
  }
  if (
    combined.includes("da") ||
    combined.includes("dưỡng") ||
    combined.includes("mặt") ||
    combined.includes("trị liệu") ||
    combined.includes("massage") ||
    combined.includes("facial")
  ) {
    return "https://images.unsplash.com/photo-1512290900673-7002b54177b5?w=1200&q=80";
  }
  return "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=1200&q=80";
}

function dayLabel(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${day}/${month}`;
}

const vnDateTime = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Ho_Chi_Minh",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function datetimeLocalValue(iso: string | null | undefined, fallbackDate: string): string {
  if (!iso) return `${fallbackDate}T09:00`;
  const parts = Object.fromEntries(
    vnDateTime.formatToParts(new Date(iso)).map((part) => [part.type, part.value]),
  );
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

function toVnOffsetIso(value: string): string {
  return `${value}:00+07:00`;
}

function canReschedule(status: string): boolean {
  return status === "approved" || status === "scheduled";
}

export function CalendarScreen() {
  const [weekStart, setWeekStart] = useState(() => startOfVnWeek(new Date()));
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal xem chi tiết & đổi giờ bài viết
  const [selectedItem, setSelectedItem] = useState<{
    item: CalendarDay["items"][number];
    fallbackDate: string;
  } | null>(null);

  const [draftTime, setDraftTime] = useState("");
  const [rescheduleError, setRescheduleError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  const today = toVnDateString(new Date());
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

  function openDetailModal(item: CalendarDay["items"][number], fallbackDate: string) {
    setSelectedItem({ item, fallbackDate });
    setDraftTime(datetimeLocalValue(item.scheduled_at, fallbackDate));
    setRescheduleError(null);
  }

  async function submitReschedule(itemId: string) {
    if (!draftTime) {
      setRescheduleError("Chọn ngày giờ đăng mới trước đã nhé.");
      return;
    }
    setSavingId(itemId);
    setRescheduleError(null);
    const result = await rescheduleItem(itemId, toVnOffsetIso(draftTime));
    setSavingId(null);
    if (!result.ok) {
      setRescheduleError(result.message);
      setReloadKey((k) => k + 1);
      return;
    }
    setSelectedItem(null);
    setReloadKey((k) => k + 1);
  }

  async function handleRepublish(itemId: string) {
    setSavingId(itemId);
    setRescheduleError(null);
    const nowIso = toVnOffsetIso(datetimeLocalValue(new Date().toISOString(), today));
    const result = await rescheduleItem(itemId, nowIso);
    setSavingId(null);
    if (!result.ok) {
      setRescheduleError(result.message);
      return;
    }
    setSelectedItem(null);
    setReloadKey((k) => k + 1);
  }

  const empty = days.every((day) => day.items.length === 0);
  const rangeLabel = days.length
    ? `${dayLabel(days[0].date)} – ${dayLabel(days[days.length - 1].date)}`
    : "";

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>Lịch đăng</h1>
        <p className={styles.subtitle}>
          Bài đã duyệt tự xếp vào đúng ngày/giờ — múi giờ Asia/Ho_Chi_Minh. Bấm vào bài để xem chi tiết.
        </p>
      </header>

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
                      <article
                        key={item.id}
                        className={styles.postCard}
                        onClick={() => openDetailModal(item, day.date)}
                        title="Bấm để xem chi tiết bài đăng"
                      >
                        <div className={styles.postMeta}>
                          <span className={styles.postTime}>
                            {item.scheduled_at
                              ? vnTime.format(new Date(item.scheduled_at))
                              : "--:--"}
                          </span>
                          <span className={styles.postId}>
                            #{item.id.slice(0, 6)}
                          </span>
                        </div>
                        <p className={styles.postTitleSnippet}>{item.text}</p>
                        <div className={styles.postMeta}>
                          <span className={styles.postChannel}>
                            {channelLabels[
                              item.channel as keyof typeof channelLabels
                            ] ?? item.channel}
                          </span>
                          <Badge tone={statusTone[item.status]}>
                            {statusLabel[item.status]}
                          </Badge>
                        </div>
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

      {/* Modal Chi tiết & Đổi giờ bài đăng */}
      {selectedItem ? (
        <div
          className={styles.modalOverlay}
          onClick={(e) => {
            if (e.target === e.currentTarget) setSelectedItem(null);
          }}
        >
          <div className={styles.modalCard} role="dialog" aria-modal="true">
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                <span className={styles.postId}>
                  #{selectedItem.item.id.slice(0, 8)}
                </span>
                <Badge tone={statusTone[selectedItem.item.status]}>
                  {statusLabel[selectedItem.item.status]}
                </Badge>
              </div>
              <Button
                variant="ghost"
                className={styles.compactButton}
                onClick={() => setSelectedItem(null)}
              >
                ✕ Đóng
              </Button>
            </div>

            <div className={styles.postMeta}>
              <span>
                ⏰ <strong>Giờ đăng:</strong>{" "}
                {selectedItem.item.scheduled_at
                  ? vnTime.format(new Date(selectedItem.item.scheduled_at)) +
                    " (Giờ VN)"
                  : "Chưa chọn giờ"}
              </span>
              <span>
                📌 <strong>Kênh:</strong>{" "}
                {channelLabels[
                  selectedItem.item.channel as keyof typeof channelLabels
                ] ?? selectedItem.item.channel}
              </span>
            </div>

            <div className={styles.modalBody}>{selectedItem.item.text}</div>

            <div className={styles.imagePreviewBox}>
              <img
                src={getTopicImage(selectedItem.item.media_note, selectedItem.item.text)}
                alt="Ảnh minh hoạ bài đăng"
                className={styles.modalPreviewImage}
              />
              <span className={styles.imageBadge}>✨ Ảnh minh hoạ AI đính kèm bài đăng</span>
            </div>

            {selectedItem.item.media_note ? (
              <div className={styles.modalMediaNote}>
                💡 <strong>Gợi ý ảnh/video:</strong> {selectedItem.item.media_note}
              </div>
            ) : null}

            <div className={styles.rescheduleSection}>
              <Button
                type="button"
                variant="outline"
                disabled={savingId === selectedItem.item.id}
                onClick={() => void handleRepublish(selectedItem.item.id)}
              >
                {savingId === selectedItem.item.id
                  ? "🔄 Đang phát lệnh đăng lại…"
                  : "🔄 Đăng lại bài này ngay (0 Token AI)"}
              </Button>
            </div>

            {canReschedule(selectedItem.item.status) ? (
              <div className={styles.rescheduleSection}>
                <h4 className={styles.rescheduleTitle}>📅 Đổi ngày giờ đăng</h4>
                <form
                  className={styles.rescheduleForm}
                  onSubmit={(e) => {
                    e.preventDefault();
                    void submitReschedule(selectedItem.item.id);
                  }}
                >
                  <Input
                    type="datetime-local"
                    value={draftTime}
                    onChange={(e) => setDraftTime(e.target.value)}
                    aria-label="Giờ đăng mới"
                  />
                  {rescheduleError ? (
                    <p className={styles.inlineError} role="alert">
                      {rescheduleError}
                    </p>
                  ) : null}
                  <div className={styles.rescheduleActions}>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setSelectedItem(null)}
                    >
                      Huỷ
                    </Button>
                    <Button
                      type="submit"
                      disabled={savingId === selectedItem.item.id}
                    >
                      {savingId === selectedItem.item.id
                        ? "Đang lưu…"
                        : "Lưu giờ mới"}
                    </Button>
                  </div>
                </form>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}
