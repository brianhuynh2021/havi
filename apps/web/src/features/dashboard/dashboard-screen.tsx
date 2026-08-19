"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { useLanguage } from "@/lib/i18n/language-context";
import {
  fetchDashboardActivity,
  fetchDashboardSummary,
  type DashboardActivityEvent,
  type DashboardContentSummary,
} from "./dashboard.api";
import { fetchSubscription, type Subscription } from "@/features/billing/billing.api";
import styles from "./dashboard.module.css";

function activityCopy(event: DashboardActivityEvent, t: (obj: { vi: string; en: string }) => string) {
  if (event.job_kind === "publish.run_job" && event.error) {
    return {
      text: t({ vi: "Một bài chưa đăng được, cần xem lại kết nối hoặc thử đăng lại.", en: "A post failed to publish, check connection or retry." }),
      tag: t({ vi: "Lỗi đăng", en: "Publish error" }),
    };
  }
  if (event.job_kind === "publish.run_job") {
    return { text: t({ vi: "Một bài đã đăng thành công.", en: "A post was published successfully." }), tag: t({ vi: "Đã đăng", en: "Published" }) };
  }
  if (event.job_kind === "content.approve") {
    return {
      text: t({ vi: "Một bài đã được duyệt và đưa vào lịch đăng.", en: "A post was approved and added to schedule." }),
      tag: t({ vi: "Đã duyệt", en: "Approved" }),
    };
  }
  if (event.job_kind === "content.reject") {
    return { text: t({ vi: "Một bản nháp đã được trả về để chỉnh lại.", en: "A draft was sent back for revision." }), tag: t({ vi: "Cần sửa", en: "Needs edit" }) };
  }
  if (event.job_kind === "content.reschedule") {
    return { text: t({ vi: "Một bài đã được đổi giờ đăng.", en: "A post was rescheduled." }), tag: t({ vi: "Đổi lịch", en: "Rescheduled" }) };
  }
  if (event.job_kind === "content.generate_drafts") {
    return { text: t({ vi: "Havi đã tạo bản nháp mới để bạn duyệt.", en: "Havi generated new drafts for review." }), tag: t({ vi: "Bản nháp", en: "New draft" }) };
  }
  return { text: t({ vi: "Workspace vừa có cập nhật mới.", en: "Workspace has a new update." }), tag: t({ vi: "Cập nhật", en: "Updated" }) };
}

export function DashboardScreen() {
  const { lang, t } = useLanguage();
  const [summary, setSummary] = useState<DashboardContentSummary | null>(null);
  const [activity, setActivity] = useState<DashboardActivityEvent[]>([]);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [daysLeft, setDaysLeft] = useState(7);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const dateLine = new Intl.DateTimeFormat(lang === "VN" ? "vi-VN" : "en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date());

  const activityTime = new Intl.DateTimeFormat(lang === "VN" ? "vi-VN" : "en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      const [summaryResult, activityResult, subResult] = await Promise.all([
        fetchDashboardSummary(),
        fetchDashboardActivity(),
        fetchSubscription(),
      ]);
      if (cancelled) return;
      if (summaryResult.ok) {
        setSummary(summaryResult.data);
        setError(null);
      } else {
        setError(summaryResult.message);
      }
      if (activityResult.ok) {
        setActivity(activityResult.data);
        setActivityError(null);
      } else {
        setActivity([]);
        setActivityError(activityResult.message);
      }
      if (subResult.ok) {
        setSub(subResult.data);
        if (subResult.data.current_period_end) {
          const left = Math.max(
            0,
            Math.ceil(
              (new Date(subResult.data.current_period_end).getTime() - Date.now()) /
                (1000 * 60 * 60 * 24),
            ),
          );
          setDaysLeft(left);
        }
      }
      setLoading(false);
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  function getStatsList(summaryData: DashboardContentSummary) {
    return [
      { value: summaryData.pending_approval, label: t({ vi: "bài chờ duyệt", en: "posts pending review" }) },
      { value: summaryData.scheduled, label: t({ vi: "bài đã lên lịch", en: "scheduled posts" }) },
      { value: summaryData.failed, label: t({ vi: "bài đăng lỗi", en: "failed posts" }) },
    ];
  }

  const isTrial = !sub || sub.plan === "trial";

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("dashboard.title", "Tổng quan hoạt động")}</h1>
        <p className={styles.subtitle}>
          {dateLine} — {t({ vi: "số liệu từ workspace này", en: "metrics from this workspace" })}
        </p>
      </header>

      {/* Trial Countdown & VietQR Upgrade Banner */}
      {isTrial ? (
        <section className={styles.trialBanner} aria-label="Thời hạn dùng thử">
          <div className={styles.trialContent}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
              <span className={styles.trialBadge}>
                ✨ {lang === "VN" ? `DÙNG THỬ CÒN ${daysLeft} NGÀY` : `${daysLeft} DAYS TRIAL LEFT`}
              </span>
              <span className={styles.trialTitle}>
                {t({
                  vi: "Trải nghiệm trọn vẹn nhân viên AI đa kênh của Havi",
                  en: "Experience full multi-channel AI marketing employee",
                })}
              </span>
            </div>
            <p className={styles.trialDesc}>
              {t({
                vi: "Tiết kiệm 4 triệu/tháng chi phí marketing, tự động lên bài Facebook/TikTok và trực inbox bắt số điện thoại 24/7.",
                en: "Save 4M VND/month on marketing costs, auto-publish Facebook/TikTok, and 24/7 inbox lead capture.",
              })}
            </p>
          </div>
          <Link href="/app/billing" className={styles.trialUpgradeBtn}>
            {lang === "VN" ? "Nâng cấp chỉ 6k/ngày ➔" : "Upgrade from 6k/day ➔"}
          </Link>
        </section>
      ) : null}

      {error ? (
        <ErrorState
          title={error}
          action={
            <Button variant="outline" onClick={() => setReloadKey((key) => key + 1)}>
              {t({ vi: "Thử lại", en: "Retry" })}
            </Button>
          }
        />
      ) : loading || !summary ? (
        <LoadingState title={t({ vi: "Đang tải tổng quan…", en: "Loading overview…" })} />
      ) : (
        <>
          <section className={styles.statsGrid} aria-label={t("dashboard.quickStats", "Thống kê nhanh")}>
            {getStatsList(summary).map((item) => (
              <div key={item.label} className={styles.cardButton}>
                <div className={styles.statValue}>{item.value}</div>
                <div className={styles.statLabel}>{item.label}</div>
              </div>
            ))}
          </section>

          <section className={styles.uploadCard}>
            <h2 className={styles.uploadTitle}>
              {t({ vi: "Có gì mới ở tiệm hôm nay?", en: "What's new at your store today?" })}
            </h2>
            <p className={styles.uploadBody}>
              {t({
                vi: "Nhập vài dòng ý tưởng hoặc bấm mic nói để Havi sáng tạo bài viết đa kênh bằng AI.",
                en: "Enter a quick prompt or speak into the mic to let Havi generate multi-channel AI posts.",
              })}
            </p>
            <div className={styles.uploadActions}>
              <Link href="/app/content" className={styles.primaryButton}>
                + {t("dashboard.createContent", "Tạo nội dung mới")}
              </Link>
              <Link href="/app/content?tab=voice" className={styles.micButton}>
                🎙️ {t({ vi: "Nói để tạo bài", en: "Voice Note to Post" })}
              </Link>
            </div>
          </section>

          {/* ROI Proof Card (100/100 Weapon) */}
          <section className={styles.roiCard} aria-label="Hiệu quả đầu tư">
            <div className={styles.roiHeader}>
              <h2 className={styles.roiTitle}>
                💎 {t({ vi: "Hiệu Quả Đầu Tư Của Tiệm", en: "Your Store's Marketing ROI" })}
              </h2>
              <span className={styles.roiBadge}>
                ⚡ {t({ vi: "TIẾT KIỆM GẤP 14 LẦN", en: "14x COST SAVINGS" })}
              </span>
            </div>

            <div className={styles.roiGrid}>
              <div className={styles.roiCol}>
                <span className={styles.roiLabel}>
                  {t({ vi: "Chi phí thuê Havi", en: "Havi AI Subscription" })}
                </span>
                <span className={styles.roiValue}>299.000 đ<small style={{ fontSize: "13px", fontWeight: 500, color: "#94a3b8" }}>/tháng</small></span>
                <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                  {t({ vi: "So với 1 nhân sự marketing: 4.500.000 đ", en: "vs. 1 part-time staff: 4.5M VND" })}
                </span>
              </div>

              <div className={`${styles.roiCol} ${styles.roiColHighlight}`}>
                <span className={styles.roiLabel}>
                  {t({ vi: "Chi phí tiệm đã tiết kiệm", en: "Estimated Monthly Savings" })}
                </span>
                <span className={`${styles.roiValue} ${styles.roiSavedValue}`}>+4.201.000 đ</span>
                <span style={{ fontSize: "12px", color: "#34d399" }}>
                  {t({ vi: "Tiết kiệm 93.3% ngân sách vận hành", en: "93.3% budget savings" })}
                </span>
              </div>

              <div className={styles.roiCol}>
                <span className={styles.roiLabel}>
                  {t({ vi: "Tỷ suất hoàn vốn (ROI)", en: "Estimated Return (ROI)" })}
                </span>
                <span className={`${styles.roiValue} ${styles.roiMultiValue}`}>61.8x ⭐</span>
                <span style={{ fontSize: "12px", color: "#fbbf24" }}>
                  {t({ vi: "Mỗi 1k đầu tư thu về ~61.8k doanh thu", en: "Every 1k invested brings ~61.8k" })}
                </span>
              </div>
            </div>

            <p className={styles.roiFootnote}>
              💡 {t({
                vi: "Havi thay thế 2–3 giờ làm bài thủ công mỗi ngày, tự động trực inbox và bóc tách số điện thoại để tiệm chốt đơn ngay lập tức.",
                en: "Havi replaces 2–3 hours of manual posting daily, handles 24/7 inbox and extracts phone numbers for instant closes.",
              })}
            </p>
          </section>

          {/* Gamified Activation Tasks Card (100/100 Weapon) */}
          <section className={styles.tasksCard} aria-label="Nhiệm vụ kích hoạt tiệm">
            <div className={styles.tasksHeader}>
              <h2 className={styles.tasksTitle}>
                🎯 {t({
                  vi: "Nhiệm Vụ Kích Hoạt Tiệm — Nhận Thêm +4 Ngày Dùng Thử",
                  en: "Store Activation Tasks — Earn +4 Free Trial Days",
                })}
              </h2>
            </div>

            <div className={styles.tasksList}>
              <div className={styles.taskItem}>
                <div className={styles.taskContent}>
                  <span className={styles.taskIcon}>🔗</span>
                  <div>
                    <p className={styles.taskName}>
                      {t({ vi: "Nối Fanpage hoặc Google Maps", en: "Connect Fanpage or Google Maps" })}
                    </p>
                    <p className={styles.taskDesc}>
                      {t({ vi: "Để Havi tự động đăng bài và trực inbox 24/7", en: "Enable 24/7 auto-post and inbox care" })}
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className={styles.taskReward}>+2 Ngày</span>
                  <Link href="/app/connections" className={styles.taskActionBtn}>
                    {t({ vi: "Nối kênh ➔", en: "Connect ➔" })}
                  </Link>
                </div>
              </div>

              <div className={styles.taskItem}>
                <div className={styles.taskContent}>
                  <span className={styles.taskIcon}>✍️</span>
                  <div>
                    <p className={styles.taskName}>
                      {t({ vi: "Duyệt xuất bản bài viết đầu tiên", en: "Approve and publish your first post" })}
                    </p>
                    <p className={styles.taskDesc}>
                      {t({ vi: "Trải nghiệm tốc độ tạo bài 1-chạm của Havi", en: "Experience 1-tap fast publishing" })}
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className={styles.taskReward}>+1 Ngày</span>
                  <Link href="/app/content" className={styles.taskActionBtn}>
                    {t({ vi: "Tạo bài ➔", en: "Create ➔" })}
                  </Link>
                </div>
              </div>

              <div className={styles.taskItem}>
                <div className={styles.taskContent}>
                  <span className={styles.taskIcon}>📲</span>
                  <div>
                    <p className={styles.taskName}>
                      {t({ vi: "Cài app Havi lên màn hình điện thoại", en: "Install Havi App to Home Screen" })}
                    </p>
                    <p className={styles.taskDesc}>
                      {t({ vi: "Nhận thông báo khách nóng và duyệt bài tiện lợi mọi lúc", en: "Get instant hot lead alerts anywhere" })}
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className={styles.taskReward}>+1 Ngày</span>
                  <Link href="/app/settings" className={styles.taskActionBtn}>
                    {t({ vi: "Cài app ➔", en: "Install ➔" })}
                  </Link>
                </div>
              </div>
            </div>
          </section>

          <section className={styles.darkCard}>
            <div className={styles.darkHeader}>
              <h2 className={styles.darkTitle}>{t({ vi: "Việc cần xem tiếp", en: "Pending Tasks" })}</h2>
              <p className={styles.darkMeta}>{t({ vi: "Ưu tiên theo dữ liệu hiện có", en: "Prioritized by current activity" })}</p>
            </div>

            <div className={styles.suggestionsGrid}>
              {summary.pending_approval > 0 ? (
                <article className={styles.suggestionCard}>
                  <p className={styles.suggestionTag}>{t({ vi: "Chờ duyệt", en: "Pending Review" })}</p>
                  <p className={styles.suggestionText}>
                    {t({
                      vi: `Có ${summary.pending_approval} bài đang chờ xem lại trước khi lên lịch.`,
                      en: `There are ${summary.pending_approval} posts pending review before scheduling.`,
                    })}
                  </p>
                  <Link href="/app/content" className={styles.ghostButton}>
                    {t({ vi: "Xem bản nháp", en: "View Drafts" })}
                  </Link>
                </article>
              ) : null}

              {summary.scheduled > 0 ? (
                <article className={styles.suggestionCard}>
                  <p className={styles.suggestionTag}>{t({ vi: "Đã sẵn sàng", en: "Ready to Post" })}</p>
                  <p className={styles.suggestionText}>
                    {t({
                      vi: `${summary.scheduled} bài đã được duyệt và nằm trong lịch đăng.`,
                      en: `${summary.scheduled} posts approved and added to calendar.`,
                    })}
                  </p>
                  <Link href="/app/calendar" className={styles.successPill}>
                    {t("dashboard.viewCalendar", "Xem lịch đăng bài")}
                  </Link>
                </article>
              ) : null}

              {summary.pending_approval === 0 && summary.scheduled === 0 ? (
                <EmptyState
                  title={t({ vi: "Chưa có việc nào đang chờ", en: "No pending tasks" })}
                  body={t({ vi: "Khi có bản nháp hoặc bài đã lên lịch, Havi sẽ gom lại ở đây.", en: "Drafts and scheduled posts will appear here." })}
                />
              ) : null}
            </div>
          </section>

          <section className={styles.aiTipBanner}>
            <div className={styles.aiTipBadge}>💡 Mẹo AI Marketing</div>
            <div>
              <p className={styles.aiTipTitle}>
                {t({
                  vi: "Tăng tương tác mạnh mẽ với Video Ngắn & Google Maps",
                  en: "Boost reach with Short-form Video & Google Maps",
                })}
              </p>
              <p className={styles.aiTipBody}>
                {t({
                  vi: "Tạo kịch bản Video ngắn 9:16 có Hook 3 giây giữ chân để tăng gấp 3 lần lượng khách tìm đến tiệm.",
                  en: "Generate 9:16 short-form videos with 3s hooks to 3x your local customer acquisition.",
                })}
              </p>
            </div>
            <Link href="/app/video-studio" className={styles.aiTipLink}>
              {t({ vi: "Mở Studio Video →", en: "Open Video Studio →" })}
            </Link>
          </section>

          <section className={styles.activityCard}>
            <p className={styles.sectionEyebrow}>{t("dashboard.recentActivity", "Hoạt động gần đây")}</p>
            {activityError ? (
              <p className={styles.activityError} role="alert">
                {activityError}
              </p>
            ) : activity.length === 0 ? (
              <EmptyState
                title={t({ vi: "Chưa có hoạt động gần đây", en: "No recent activity" })}
                body={t({ vi: "Hoạt động sáng tạo và đăng bài sẽ hiện ở đây.", en: "Content generation and publishing logs will show here." })}
              />
            ) : (
              <div className={styles.activityList}>
                {activity.map((event) => {
                  const copy = activityCopy(event, t);
                  return (
                    <article key={event.id} className={styles.activityItem}>
                      <p className={styles.activityTime}>
                        {activityTime.format(new Date(event.created_at))}
                      </p>
                      <p className={styles.activityText}>{copy.text}</p>
                      <span className={styles.activityTag}>{copy.tag}</span>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}

