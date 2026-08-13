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
      const [summaryResult, activityResult] = await Promise.all([
        fetchDashboardSummary(),
        fetchDashboardActivity(),
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

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("dashboard.title", "Tổng quan hoạt động")}</h1>
        <p className={styles.subtitle}>
          {dateLine} — {t({ vi: "số liệu từ workspace này", en: "metrics from this workspace" })}
        </p>
      </header>

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
                vi: "Nhập vài dòng ý tưởng để Havi sáng tạo bài viết đa kênh bằng AI.",
                en: "Enter a quick prompt to let Havi generate multi-channel AI posts.",
              })}
            </p>
            <Link href="/app/content" className={styles.primaryButton}>
              + {t("dashboard.createContent", "Tạo nội dung mới")}
            </Link>
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

          <section className={styles.zaloBanner}>
            <div className={styles.zaloBadge}>Zalo</div>
            <div>
              <p className={styles.zaloTitle}>{t({ vi: "Duyệt qua Zalo OA", en: "Review via Zalo OA" })}</p>
              <p className={styles.zaloBody}>
                {t({
                  vi: "Thông báo qua Zalo OA sắp ra mắt. Hiện duyệt trực tiếp trên web.",
                  en: "Zalo OA notifications coming soon. Review directly on web.",
                })}
              </p>
            </div>
            <span className={styles.statusPill}>{t({ vi: "Sắp có", en: "Coming soon" })}</span>
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

