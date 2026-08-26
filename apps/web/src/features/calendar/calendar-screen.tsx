"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { channelLabels } from "@/features/content-creation/content-creation.fixture";
import { useLanguage } from "@/lib/i18n/language-context";
import { FailedPostsPanel } from "@/features/publish-jobs/failed-posts-panel";
import {
  addDays,
  fetchCalendar,
  rescheduleItem,
  startOfVnWeek,
  startOfVnMonthGrid,
  toVnDateString,
  type CalendarDay,
} from "./calendar.api";
import { rejectItem } from "@/features/content-creation/content-creation.api";
import { statusLabel, statusTone } from "./calendar.fixture";
import styles from "./calendar.module.css";

/** Giờ đăng hiện theo giờ VN, không theo giờ máy. */
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
  const { lang, t } = useLanguage();
  const [baseDate, setBaseDate] = useState<string>(() => toVnDateString(new Date()));
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // View switch: "week" (lưới 7 ngày) | "month" (lưới 42 ngày) | "timeline" (danh sách dòng thời gian)
  const [viewMode, setViewMode] = useState<"week" | "month" | "timeline">("week");
  const [channelFilter, setChannelFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const [selectedItem, setSelectedItem] = useState<{
    item: CalendarDay["items"][number];
    date: string;
  } | null>(null);

  const [targetIso, setTargetIso] = useState("");
  const [rescheduling, setRescheduling] = useState(false);
  const [rescheduleError, setRescheduleError] = useState<string | null>(null);

  const weekdayLabels = lang === "VN"
    ? ["Th 2", "Th 3", "Th 4", "Th 5", "Th 6", "Th 7", "CN"]
    : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  const fullWeekdayLabels = lang === "VN"
    ? ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    : ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

  const today = toVnDateString(new Date());

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);

      let startDateStr = "";
      let endDateStr = "";

      if (viewMode === "month") {
        const gridStart = startOfVnMonthGrid(new Date(baseDate));
        startDateStr = toVnDateString(gridStart);
        endDateStr = toVnDateString(addDays(gridStart, 41)); // 6 weeks = 42 days
      } else {
        const weekStart = startOfVnWeek(new Date(baseDate));
        startDateStr = toVnDateString(weekStart);
        endDateStr = toVnDateString(addDays(weekStart, 6)); // 7 days
      }

      const result = await fetchCalendar(startDateStr, endDateStr);
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
  }, [baseDate, viewMode, reloadKey]);

  const handleDragStart = (e: React.DragEvent, item: CalendarDay["items"][number]) => {
    e.dataTransfer.setData("application/json", JSON.stringify(item));
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault(); // Necessary to allow dropping
    e.dataTransfer.dropEffect = "move";
  };

  const handleDrop = async (e: React.DragEvent, targetDate: string) => {
    e.preventDefault();
    try {
      const dataStr = e.dataTransfer.getData("application/json");
      if (!dataStr) return;
      const item = JSON.parse(dataStr) as CalendarDay["items"][number];
      
      if (!canReschedule(item.status)) {
        alert("Chỉ có thể đổi giờ bài đang chờ đăng hoặc đã duyệt.");
        return;
      }
      
      const oldTime = item.scheduled_at ? new Date(item.scheduled_at) : null;
      let newTargetIso = "";
      if (oldTime) {
        const parts = Object.fromEntries(
          vnDateTime.formatToParts(oldTime).map((part) => [part.type, part.value]),
        );
        newTargetIso = `${targetDate}T${parts.hour}:${parts.minute}`;
      } else {
        newTargetIso = `${targetDate}T09:00`;
      }
      
      const newOffsetIso = toVnOffsetIso(newTargetIso);
      if (newOffsetIso === item.scheduled_at) return; 
      
      setRescheduling(true);
      const result = await rescheduleItem(item.id, newOffsetIso);
      setRescheduling(false);
      
      if (!result.ok) {
        alert(result.message);
      }
      setReloadKey(k => k + 1);
      
    } catch (err) {
      console.error("Drop error", err);
    }
  };

  function openDetailModal(item: CalendarDay["items"][number], date: string) {
    setSelectedItem({ item, date });
    setTargetIso(datetimeLocalValue(item.scheduled_at, date));
    setRescheduleError(null);
  }

  async function submitReschedule() {
    if (!selectedItem) return;
    setRescheduling(true);
    setRescheduleError(null);
    const result = await rescheduleItem(selectedItem.item.id, toVnOffsetIso(targetIso));
    setRescheduling(false);
    if (!result.ok) {
      setRescheduleError(result.message);
      setReloadKey((k) => k + 1);
      return;
    }
    setSelectedItem(null);
    setReloadKey((k) => k + 1);
  }

  const [cancelling, setCancelling] = useState(false);

  async function handleCancelScheduledPost() {
    if (!selectedItem) return;
    setCancelling(true);
    setRescheduleError(null);
    const result = await rejectItem(selectedItem.item.id);
    setCancelling(false);
    if (!result.ok) {
      setRescheduleError(result.message);
      return;
    }
    setSelectedItem(null);
    setReloadKey((k) => k + 1);
  }

  function applyPresetTime(timeStr: string) {
    if (!targetIso) return;
    const datePart = targetIso.split("T")[0];
    setTargetIso(`${datePart}T${timeStr}`);
  }

  // Lọc bài theo Kênh và Trạng thái
  const filteredDays = useMemo(() => {
    return days.map((day) => ({
      ...day,
      items: day.items.filter((item) => {
        if (item.status === "draft") return false;
        const matchesChannel =
          channelFilter === "all" ||
          item.channel === channelFilter ||
          (channelFilter === "facebook_page" && item.channel === "reels");
        const matchesStatus =
          statusFilter === "all" || item.status === statusFilter;
        return matchesChannel && matchesStatus;
      }),
    }));
  }, [days, channelFilter, statusFilter]);

  const totalItems = days.reduce((sum, d) => sum + d.items.length, 0);
  const uniqueChannels = Array.from(
    new Set(days.flatMap((d) => d.items.map((i) => i.channel))),
  );

  const empty = days.every((day) => day.items.length === 0);
  const rangeLabel = days.length
    ? `${dayLabel(days[0].date)} – ${dayLabel(days[days.length - 1].date)}`
    : "";

  return (
    <>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>{t("calendar.title", "Lịch Đăng Bài")}</h1>
          <Badge tone="success">✨ Múi giờ Asia/Ho_Chi_Minh (UTC+7)</Badge>
        </div>
        <p className={styles.subtitle}>
          {t({
            vi: "Bài đã duyệt được xếp theo thời gian bạn chọn. Chỉ kênh đang được backend hỗ trợ và đã cấp quyền mới có thể xuất bản.",
            en: "Approved posts follow the time you choose. Only backend-supported channels with valid permissions can publish.",
          })}
        </p>

        {/* Dashboard Thống Kê Tổng Quan */}
        <div className={styles.metricsBar}>
          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>📅 Tổng bài lên lịch</span>
            <span className={styles.metricValue}>{totalItems} bài</span>
            <span className={styles.metricSubtext}>Tuần đang hiển thị</span>
          </div>
          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>📢 Kênh kết nối</span>
            <span className={styles.metricValue}>{uniqueChannels.length || 0} kênh</span>
            <span className={styles.metricSubtext}>Facebook, TikTok, YouTube</span>
          </div>
          <div className={styles.metricCard}>
            <span className={styles.metricLabel}>⚡ Tự động đăng</span>
            <span className={styles.metricValue}>Giờ Vàng VN</span>
            <span className={styles.metricSubtext}>08:00 • 12:00 • 20:00 ICT</span>
          </div>
        </div>
      </header>

      <FailedPostsPanel onPublished={() => setReloadKey((k) => k + 1)} />

      {/* Control Panel: Tuần, Bộ Lọc và Chuyển đổi View */}
      <div className={styles.controlPanel}>
        <div className={styles.weekBar}>
          <Button
            variant="outline"
            onClick={() => setBaseDate((d) => toVnDateString(addDays(new Date(d), viewMode === "month" ? -28 : -7)))}
          >
            ← {t({ vi: "Trước", en: "Prev" })}
          </Button>
          <span className={styles.weekRange}>📅 {rangeLabel}</span>
          <div className={styles.weekActions}>
            <Button
              variant="outline"
              onClick={() => setBaseDate(toVnDateString(new Date()))}
            >
              {t({ vi: "Hiện tại", en: "Current" })}
            </Button>
            <Button
              variant="outline"
              onClick={() => setBaseDate((d) => toVnDateString(addDays(new Date(d), viewMode === "month" ? 28 : 7)))}
            >
              {t({ vi: "Sau", en: "Next" })} →
            </Button>
          </div>
        </div>

        <div className={styles.filterBar}>
          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>Kênh:</span>
            <button
              type="button"
              className={`${styles.filterChip} ${channelFilter === "all" ? styles.filterChipActive : ""}`}
              onClick={() => setChannelFilter("all")}
            >
              Tất cả
            </button>
            <button
              type="button"
              className={`${styles.filterChip} ${channelFilter === "facebook_page" ? styles.filterChipActive : ""}`}
              onClick={() => setChannelFilter("facebook_page")}
            >
              Facebook
            </button>
            <button
              type="button"
              className={`${styles.filterChip} ${channelFilter === "tiktok" ? styles.filterChipActive : ""}`}
              onClick={() => setChannelFilter("tiktok")}
            >
              TikTok
            </button>
            <button
              type="button"
              className={`${styles.filterChip} ${channelFilter === "youtube" ? styles.filterChipActive : ""}`}
              onClick={() => setChannelFilter("youtube")}
            >
              YouTube
            </button>
          </div>

          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>Trạng thái:</span>
            <button
              type="button"
              className={`${styles.filterChip} ${statusFilter === "all" ? styles.filterChipActive : ""}`}
              onClick={() => setStatusFilter("all")}
            >
              Tất cả
            </button>
            <button
              type="button"
              className={`${styles.filterChip} ${statusFilter === "scheduled" ? styles.filterChipActive : ""}`}
              onClick={() => setStatusFilter("scheduled")}
            >
              Chờ đăng
            </button>
            <button
              type="button"
              className={`${styles.filterChip} ${statusFilter === "published" ? styles.filterChipActive : ""}`}
              onClick={() => setStatusFilter("published")}
            >
              Đã đăng
            </button>
          </div>

          {/* View Mode Switcher */}
          <div className={styles.viewSwitcher}>
            <button
              type="button"
              className={`${styles.viewBtn} ${viewMode === "week" ? styles.viewBtnActive : ""}`}
              onClick={() => setViewMode("week")}
            >
              📊 Lưới tuần
            </button>
            <button
              type="button"
              className={`${styles.viewBtn} ${viewMode === "month" ? styles.viewBtnActive : ""}`}
              onClick={() => setViewMode("month")}
            >
              🗓️ Lưới tháng
            </button>
            <button
              type="button"
              className={`${styles.viewBtn} ${viewMode === "timeline" ? styles.viewBtnActive : ""}`}
              onClick={() => setViewMode("timeline")}
            >
              📋 Dòng thời gian
            </button>
          </div>
        </div>
      </div>

      {error ? (
        <ErrorState
          title={error}
          action={
            <Button variant="outline" onClick={() => setReloadKey((k) => k + 1)}>
              {t({ vi: "Thử lại", en: "Retry" })}
            </Button>
          }
        />
      ) : loading ? (
        <LoadingState title={t({ vi: "Đang tải lịch…", en: "Loading calendar…" })} />
      ) : (
        <>
          {/* CHẾ ĐỘ 1 & 2: LƯỚI TUẦN / LƯỚI THÁNG */}
          {viewMode === "week" || viewMode === "month" ? (
            <section className={viewMode === "month" ? styles.monthGrid : styles.grid} aria-label={t("calendar.title", "Lịch đăng bài")}>
              {/* Nếu là lưới tháng, hiển thị thêm hàng tiêu đề các thứ */}
              {viewMode === "month" && (
                <div className={styles.monthHeaderRow}>
                  {fullWeekdayLabels.map((label) => (
                    <div key={label} className={styles.monthHeaderCell}>{label}</div>
                  ))}
                </div>
              )}
              {filteredDays.map((day, index) => (
                <div
                  key={day.date}
                  className={`${viewMode === "month" ? styles.monthDayCell : styles.dayColumn} ${
                    day.date === today ? styles.dayColumnToday : ""
                  }`}
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, day.date)}
                >
                  <div className={styles.dayHeader}>
                    <div className={styles.dayHeaderTitleRow}>
                      {viewMode === "week" && <span className={styles.dayLabel}>{weekdayLabels[index]}</span>}
                      {day.date === today ? (
                        <span className={styles.todayPill}>Hôm nay</span>
                      ) : null}
                    </div>
                    <span className={styles.dayDate}>{viewMode === "month" ? new Date(day.date).getDate() : dayLabel(day.date)}</span>
                  </div>

                  {day.items.length === 0 ? (
                    <div className={styles.emptySlot} title="Chưa có bài lên lịch cho ngày này">
                      <span className={styles.emptySlotIcon}>+</span>
                      {viewMode === "week" && <span className={styles.emptySlotText}>{t({ vi: "Chưa có bài", en: "No posts" })}</span>}
                    </div>
                  ) : (
                    <div className={styles.postList}>
                      {day.items.map((item) => (
                        <article
                          key={item.id}
                          className={styles.postCard}
                          draggable={canReschedule(item.status)}
                          onDragStart={(e) => handleDragStart(e, item)}
                          onClick={() => openDetailModal(item, day.date)}
                          title="Bấm để xem chi tiết bài đăng"
                        >
                          <div className={styles.postMeta}>
                            <span className={styles.postTime}>
                              {item.scheduled_at
                                ? vnTime.format(new Date(item.scheduled_at))
                                : "--:--"}
                            </span>
                            {viewMode === "week" && (
                              <Badge tone={statusTone[item.status]}>
                                {statusLabel[item.status]}
                              </Badge>
                            )}
                          </div>
                          {viewMode === "week" && <p className={styles.postTitleSnippet}>{item.text}</p>}
                          <div className={styles.postFooter}>
                            <span className={styles.channelBadge}>
                              {channelLabels[
                                item.channel as keyof typeof channelLabels
                              ] ?? item.channel}
                            </span>
                            {viewMode === "week" && (
                              <span className={styles.postId}>
                                #{item.id.slice(0, 6)}
                              </span>
                            )}
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </section>
          ) : (
            /* CHẾ ĐỘ 2: DÒNG THỜI GIAN CHI TIẾT (TIMELINE / DEBUG LIST VIEW) */
            <section className={styles.timelineContainer} aria-label="Dòng thời gian bài đăng">
              {filteredDays.filter((d) => d.items.length > 0).length === 0 ? (
                <EmptyState
                  title="Không có bài nào khớp với bộ lọc"
                  body="Hãy chọn 'Tất cả' hoặc duyệt bài mới để xem dòng thời gian bài đăng."
                />
              ) : (
                filteredDays
                  .filter((day) => day.items.length > 0)
                  .map((day, dIdx) => (
                    <div key={day.date} className={styles.timelineDaySection}>
                      <div className={styles.timelineDayHeader}>
                        <div className={styles.timelineDayTitle}>
                          <span>📅 {fullWeekdayLabels[dIdx % 7]}, {dayLabel(day.date)}</span>
                          {day.date === today ? (
                            <span className={styles.todayPill}>Hôm nay</span>
                          ) : null}
                        </div>
                        <span className={styles.timelineDayCount}>{day.items.length} bài đăng</span>
                      </div>

                      <div className={styles.timelineList}>
                        {day.items.map((item) => (
                          <div
                            key={item.id}
                            className={styles.timelineRow}
                            onClick={() => openDetailModal(item, day.date)}
                          >
                            <div className={styles.timelineRowLeft}>
                              <div className={styles.timelineTimeBox}>
                                <span className={styles.timelineTime}>
                                  {item.scheduled_at
                                    ? vnTime.format(new Date(item.scheduled_at))
                                    : "--:--"}
                                </span>
                                <span className={styles.timelineChannelText}>
                                  {item.channel.includes("facebook") ? "FB" : item.channel.includes("tiktok") ? "TikTok" : item.channel.includes("youtube") ? "YouTube" : "Kênh"}
                                </span>
                              </div>
                              {item.media_url ? (
                                <img
                                  src={item.media_url}
                                  alt="Thumb"
                                  className={styles.timelineThumb}
                                />
                              ) : (
                                <div className={styles.timelineThumb} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--surface-sunken)', color: 'var(--text-muted)' }}>
                                  📝
                                </div>
                              )}
                              <div className={styles.timelineContent}>
                                <div className={styles.timelineSnippet}>{item.text}</div>
                                <div className={styles.timelineRowMeta}>
                                  <span className={styles.postId}>ID: #{item.id.slice(0, 8)}</span>
                                  <span>•</span>
                                  <span>{channelLabels[item.channel as keyof typeof channelLabels] ?? item.channel}</span>
                                </div>
                              </div>
                            </div>

                            <div className={styles.timelineRowRight}>
                              <Badge tone={statusTone[item.status]}>
                                {statusLabel[item.status]}
                              </Badge>
                              <Button variant="outline">
                                Xem & Đổi giờ
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
              )}
            </section>
          )}

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

            {selectedItem.item.media_url ? (
              <div className={styles.imagePreviewBox}>
                <img
                  src={selectedItem.item.media_url}
                  alt="Ảnh đính kèm"
                  className={styles.modalPreviewImage}
                />
              </div>
            ) : null}

            {selectedItem.item.media_note ? (
              <div className={styles.modalMediaNote}>
                💡 <strong>Gợi ý ảnh/video:</strong> {selectedItem.item.media_note}
              </div>
            ) : null}

            {canReschedule(selectedItem.item.status) ? (
              <div className={styles.rescheduleSection}>
                <h4 className={styles.rescheduleTitle}>📅 Đổi ngày giờ đăng (Giờ vàng ICT)</h4>

                {/* Quick Presets for Shop Owners */}
                <div className={styles.presetGrid}>
                  <button
                    type="button"
                    className={styles.presetBtn}
                    onClick={() => applyPresetTime("08:00")}
                  >
                    🌅 Sáng (08:00)
                  </button>
                  <button
                    type="button"
                    className={styles.presetBtn}
                    onClick={() => applyPresetTime("12:00")}
                  >
                    ☀️ Trưa (12:00)
                  </button>
                  <button
                    type="button"
                    className={styles.presetBtn}
                    onClick={() => applyPresetTime("20:00")}
                  >
                    🌆 Tối (20:00)
                  </button>
                  <button
                    type="button"
                    className={styles.presetBtn}
                    onClick={() => applyPresetTime("21:30")}
                  >
                    🌙 Đêm (21:30)
                  </button>
                </div>

                <form
                  className={styles.rescheduleForm}
                  onSubmit={(e) => {
                    e.preventDefault();
                    void submitReschedule();
                  }}
                >
                  <Input
                    type="datetime-local"
                    value={targetIso}
                    onChange={(e) => setTargetIso(e.target.value)}
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
                      variant="outline"
                      style={{ color: "#D97706", borderColor: "#FCD34D", background: "#FFFBEB" }}
                      disabled={cancelling}
                      onClick={handleCancelScheduledPost}
                    >
                      {cancelling ? "Đang chuyển…" : "⏸️ Hoãn lại về Bản nháp"}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setSelectedItem(null)}
                    >
                      Đóng
                    </Button>
                    <Button
                      type="submit"
                      disabled={rescheduling}
                    >
                      {rescheduling ? "Đang lưu…" : "Lưu giờ mới"}
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
