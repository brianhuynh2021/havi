"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import {
  fetchDashboardActivity,
  fetchDashboardSummary,
  type DashboardActivityEvent,
  type DashboardContentSummary,
} from "./dashboard.api";
import styles from "./dashboard.module.css";

const dateLine = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  weekday: "long",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
}).format(new Date());

function stats(summary: DashboardContentSummary) {
  return [
    { value: summary.pending_approval, label: "bài chờ duyệt" },
    { value: summary.scheduled, label: "bài đã lên lịch" },
    { value: summary.failed, label: "bài đăng lỗi" },
  ];
}

const activityTime = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function activityCopy(event: DashboardActivityEvent) {
  if (event.job_kind === "publish.run_job" && event.error) {
    return {
      text: "Một bài chưa đăng được, cần xem lại kết nối hoặc thử đăng lại.",
      tag: "Lỗi đăng",
    };
  }
  if (event.job_kind === "publish.run_job") {
    return { text: "Một bài đã đăng thành công.", tag: "Đã đăng" };
  }
  if (event.job_kind === "content.approve") {
    return {
      text: "Một bài đã được duyệt và đưa vào lịch đăng.",
      tag: "Đã duyệt",
    };
  }
  if (event.job_kind === "content.reject") {
    return { text: "Một bản nháp đã được trả về để chỉnh lại.", tag: "Cần sửa" };
  }
  if (event.job_kind === "content.reschedule") {
    return { text: "Một bài đã được đổi giờ đăng.", tag: "Đổi lịch" };
  }
  if (event.job_kind === "content.generate_drafts") {
    return { text: "Havi đã tạo bản nháp mới để chị duyệt.", tag: "Bản nháp" };
  }
  return { text: "Workspace vừa có cập nhật mới.", tag: "Cập nhật" };
}

export function DashboardScreen() {
  const [summary, setSummary] = useState<DashboardContentSummary | null>(null);
  const [activity, setActivity] = useState<DashboardActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

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

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>Tổng quan hôm nay</h1>
        <p className={styles.subtitle}>
          {dateLine} — số liệu lấy từ nội dung thật trong workspace này.
        </p>
      </header>

      {error ? (
        <ErrorState
          title={error}
          action={
            <Button variant="outline" onClick={() => setReloadKey((key) => key + 1)}>
              Thử lại
            </Button>
          }
        />
      ) : loading || !summary ? (
        <LoadingState title="Đang tải tổng quan…" />
      ) : (
        <>
          <section className={styles.statsGrid} aria-label="Thống kê nhanh">
            {stats(summary).map((item) => (
              <div key={item.label} className={styles.cardButton}>
                <div className={styles.statValue}>{item.value}</div>
                <div className={styles.statLabel}>{item.label}</div>
              </div>
            ))}
          </section>

          <section className={styles.uploadCard}>
            <h2 className={styles.uploadTitle}>Có gì mới ở tiệm hôm nay?</h2>
            <p className={styles.uploadBody}>
              Thả ảnh hoặc gõ vài dòng để Havi viết nhiều bản nháp theo kênh.
              Chị vẫn duyệt trước khi bài được lên lịch.
            </p>
            <Link href="/noi-dung" className={styles.primaryButton}>
              + Tạo nội dung mới
            </Link>
          </section>

          <section className={styles.darkCard}>
            <div className={styles.darkHeader}>
              <h2 className={styles.darkTitle}>Việc cần xem tiếp</h2>
              <p className={styles.darkMeta}>Ưu tiên theo dữ liệu hiện có</p>
            </div>

            <div className={styles.suggestionsGrid}>
              {summary.pending_approval > 0 ? (
                <article className={styles.suggestionCard}>
                  <p className={styles.suggestionTag}>Chờ chị duyệt</p>
                  <p className={styles.suggestionText}>
                    Có {summary.pending_approval} bài đang chờ xem lại trước khi
                    lên lịch.
                  </p>
                  <Link href="/noi-dung" className={styles.ghostButton}>
                    Xem bản nháp
                  </Link>
                </article>
              ) : null}

              {summary.scheduled > 0 ? (
                <article className={styles.suggestionCard}>
                  <p className={styles.suggestionTag}>Đã sẵn sàng</p>
                  <p className={styles.suggestionText}>
                    {summary.scheduled} bài đã được duyệt và đang nằm trong lịch.
                  </p>
                  <Link href="/lich-dang" className={styles.successPill}>
                    Mở lịch đăng
                  </Link>
                </article>
              ) : null}

              {summary.pending_approval === 0 && summary.scheduled === 0 ? (
                <EmptyState
                  title="Chưa có việc nào đang chờ"
                  body="Khi có bản nháp hoặc bài đã lên lịch, Havi sẽ gom lại ở đây."
                />
              ) : null}
            </div>
          </section>

          <section className={styles.zaloBanner}>
            <div className={styles.zaloBadge}>Zalo</div>
            <div>
              <p className={styles.zaloTitle}>Duyệt qua Zalo OA</p>
              <p className={styles.zaloBody}>
                Nhắc duyệt qua Zalo là hạng mục P1. Pilot hiện duyệt trực tiếp
                trong web để giữ vòng đăng bài an toàn.
              </p>
            </div>
            <span className={styles.statusPill}>Sắp có</span>
          </section>

          <section className={styles.activityCard}>
            <p className={styles.sectionEyebrow}>Hoạt động gần đây</p>
            {activityError ? (
              <p className={styles.activityError} role="alert">
                {activityError}
              </p>
            ) : activity.length === 0 ? (
              <EmptyState
                title="Chưa có hoạt động gần đây"
                body="Khi Havi tạo, duyệt, đổi lịch hoặc đăng bài, hoạt động sẽ hiện ở đây."
              />
            ) : (
              <div className={styles.activityList}>
                {activity.map((event) => {
                  const copy = activityCopy(event);
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
