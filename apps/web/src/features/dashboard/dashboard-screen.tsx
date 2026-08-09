"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import {
  fetchDashboardSummary,
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

export function DashboardScreen() {
  const [summary, setSummary] = useState<DashboardContentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      const result = await fetchDashboardSummary();
      if (cancelled) return;
      if (result.ok) {
        setSummary(result.data);
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
            {summary.published === 0 && summary.failed === 0 ? (
              <EmptyState
                title="Chưa có bài đã đăng"
                body="Sau khi scheduler đăng bài thật, hoạt động sẽ hiện ở đây."
              />
            ) : (
              <div className={styles.activityList}>
                {summary.published > 0 ? (
                  <article className={styles.activityItem}>
                    <p className={styles.activityTime}>Tuần này</p>
                    <p className={styles.activityText}>
                      {summary.published} bài đã đăng thành công.
                    </p>
                    <span className={styles.activityTag}>Đã đăng</span>
                  </article>
                ) : null}
                {summary.failed > 0 ? (
                  <article className={styles.activityItem}>
                    <p className={styles.activityTime}>Cần xử lý</p>
                    <p className={styles.activityText}>
                      {summary.failed} bài đăng lỗi đang chờ xem lại.
                    </p>
                    <span className={styles.activityTag}>Lỗi</span>
                  </article>
                ) : null}
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}
