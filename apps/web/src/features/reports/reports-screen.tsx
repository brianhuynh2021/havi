"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import {
  fetchReports,
  type ChannelAttribution,
  type ReportsData,
} from "./reports.api";
import styles from "./reports.module.css";

const channelLabels: Record<string, string> = {
  facebook_page: "Facebook Page",
  zalo_oa: "Zalo OA",
  google_business: "Google Business",
  reels: "Reels",
  tiktok: "TikTok",
  youtube: "YouTube",
  email: "Email",
};

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function insight(data: ReportsData): string {
  if (data.summary.published_posts === 0) {
    return "Tháng này chưa có bài nào được ghi nhận là đã đăng. Khi có publish job thành công, Havi sẽ bắt đầu tổng hợp nhịp đăng ở đây.";
  }
  if (data.summary.new_leads === 0) {
    return `Tháng này đã có ${data.summary.published_posts} bài đăng thành công. Lead và engagement snapshot chưa được nối, nên Havi chưa kết luận bài nào kéo khách tốt hơn.`;
  }
  return `Tháng này đã có ${data.summary.published_posts} bài đăng và ${data.summary.new_leads} lead được ghi nhận.`;
}

function statCards(data: ReportsData) {
  return [
    { label: "Bài đã đăng", value: String(data.summary.published_posts) },
    { label: "Lead đã ghi nhận", value: String(data.summary.new_leads) },
    { label: "Tỷ lệ chốt", value: percent(data.summary.lead_won_rate) },
  ];
}

function attributionPercent(item: ChannelAttribution): number {
  return Math.max(0, Math.min(100, Math.round(item.share * 100)));
}

export function ReportsScreen() {
  const [data, setData] = useState<ReportsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      const result = await fetchReports();
      if (cancelled) return;
      if (result.ok) {
        setData(result.data);
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

  const maxPosts = Math.max(
    ...(data?.timeseries.points.map((point) => point.value) ?? [0]),
    1,
  );

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>Báo cáo</h1>
        <p className={styles.subtitle}>
          Số liệu đang dựa trên bài đã đăng thật trong workspace này.
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
      ) : loading || !data ? (
        <LoadingState title="Đang tải báo cáo…" />
      ) : (
        <>
          <section className={styles.insightCard} aria-label="Nhận xét của Havi">
            <p className={styles.insightLabel}>Havi nhận xét</p>
            <p className={styles.insightText}>{insight(data)}</p>
          </section>

          <section className={styles.statsGrid} aria-label="Thống kê tháng">
            {statCards(data).map((item) => (
              <div key={item.label} className={styles.statCard}>
                <div className={styles.statValue}>{item.value}</div>
                <div className={styles.statLabel}>{item.label}</div>
              </div>
            ))}
          </section>

          <section className={styles.chartCard} aria-label="Bài đăng theo tuần">
            <h2 className={styles.sectionTitle}>Bài đăng theo tuần</h2>
            <div className={styles.chartBars}>
              {data.timeseries.points.map((point) => (
                <div key={point.period} className={styles.chartColumn}>
                  <div
                    className={styles.chartBar}
                    style={{ height: `${(point.value / maxPosts) * 100}%` }}
                    aria-hidden="true"
                  />
                  <span className={styles.chartValue}>{point.value}</span>
                  <span className={styles.chartLabel}>{point.period}</span>
                </div>
              ))}
            </div>
          </section>

          <section className={styles.attributionCard} aria-label="Bài đã đăng theo kênh">
            <h2 className={styles.sectionTitle}>Bài đã đăng theo kênh</h2>
            {data.attribution.length === 0 ? (
              <EmptyState
                title="Chưa có bài đã đăng"
                body="Khi Facebook publish thành công, tỷ trọng theo kênh sẽ hiện ở đây."
              />
            ) : (
              <div className={styles.attributionList}>
                {data.attribution.map((item) => {
                  const value = attributionPercent(item);
                  return (
                    <div key={item.channel} className={styles.attributionRow}>
                      <span className={styles.attributionLabel}>
                        {channelLabels[item.channel] ?? item.channel}
                      </span>
                      <div className={styles.attributionTrack}>
                        <div
                          className={styles.attributionFill}
                          style={{ width: `${value}%` }}
                        />
                      </div>
                      <span className={styles.attributionPercent}>{value}%</span>
                    </div>
                  );
                })}
              </div>
            )}
            <p className={styles.dataNote}>
              Engagement snapshot và lead attribution chưa nối, nên phần này tạm
              tính theo bài đã đăng.
            </p>
          </section>
        </>
      )}
    </>
  );
}
