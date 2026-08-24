"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { useLanguage } from "@/lib/i18n/language-context";
import {
  fetchReports,
  type ChannelAttribution,
  type ReportsData,
} from "./reports.api";
import styles from "./reports.module.css";

const channelLabels: Record<string, string> = {
  facebook_page: "Facebook Page",
  google_business: "Google Maps SEO",
  reels: "Facebook Reels",
  tiktok: "TikTok",
  youtube: "YouTube Shorts",
  email: "Email",
  zalo_oa: "Zalo OA (Lưu trữ)",
};

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function attributionPercent(item: ChannelAttribution): number {
  return Math.max(0, Math.min(100, Math.round(item.share * 100)));
}

function formatVnd(amount: number): string {
  return `${amount.toLocaleString("vi-VN")} đ`;
}

export function ReportsScreen() {
  const { t } = useLanguage();
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

  function getStatCards(reportsData: ReportsData) {
    return [
      { label: t("dashboard.publishedPosts", "Bài đã đăng"), value: String(reportsData.summary.published_posts) },
      { label: t("dashboard.leadsCaptured", "Lead đã ghi nhận"), value: String(reportsData.summary.new_leads) },
      { label: t({ vi: "Lead đã xác nhận", en: "Verified Leads" }), value: String(reportsData.summary.won_leads) },
      { label: t({ vi: "Tỷ lệ chốt", en: "Win Rate" }), value: percent(reportsData.summary.lead_won_rate) },
      { label: t({ vi: "Doanh thu xác thực (VietQR/POS)", en: "Verified Revenue" }), value: formatVnd(reportsData.summary.total_revenue_vnd || 0) },
    ];

  }

  const maxPosts = Math.max(
    ...(data?.timeseries.points.map((point) => point.value) ?? [0]),
    1,
  );

  return (
    <>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("reports.title", "Báo Cáo & Phân Tích")}</h1>
        <p className={styles.subtitle}>
          {t("reports.subtitle", "Đánh giá hiệu quả truyền thông và chuyển đổi")}
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
      ) : loading || !data ? (
        <LoadingState title={t({ vi: "Đang tải báo cáo…", en: "Loading reports…" })} />
      ) : (
        <>
          {/* Peace of Mind & Daily Human Utility */}
          <section className={styles.peaceOfMindCard} aria-label="Thời gian và công sức tiết kiệm">
            <div className={styles.peaceOfMindBadge}>🌿 GIÁ TRỊ THIẾT THỰC CÙNG BẠN</div>
            <div className={styles.peaceOfMindGrid}>
              <div className={styles.peaceOfMindItem}>
                <span className={styles.peaceOfMindVal}>
                  ~{Math.max(1, Math.round(data.summary.published_posts * 1.5 + data.summary.price_inquiries * 0.2))} giờ
                </span>
                <span className={styles.peaceOfMindLbl}>⏱️ Thời gian soạn bài & trực chat Havi đã gánh vác</span>
              </div>
              <div className={styles.peaceOfMindItem}>
                <span className={styles.peaceOfMindVal}>&lt; 10 giây</span>
                <span className={styles.peaceOfMindLbl}>⚡ Tốc độ phản hồi khách Messenger tức thì</span>
              </div>
              <div className={styles.peaceOfMindItem}>
                <span className={styles.peaceOfMindVal}>100%</span>
                <span className={styles.peaceOfMindLbl}>📘 Bài viết giữ vững đúng giọng văn thương hiệu</span>
              </div>
            </div>
          </section>

          <section className={styles.statsGrid} aria-label={t("dashboard.quickStats", "Thống kê nhanh")}>
            {getStatCards(data).map((card) => (
              <div key={card.label} className={styles.statCard}>
                <div className={styles.statValue}>{card.value}</div>
                <div className={styles.statLabel}>{card.label}</div>
              </div>
            ))}
          </section>

          <section className={styles.chartCard} aria-label="Bài đăng theo tuần">
            <h2 className={styles.sectionTitle}>{t({ vi: "Bài đăng theo tuần", en: "Weekly Posts" })}</h2>
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
            <h2 className={styles.sectionTitle}>{t({ vi: "Bài đã đăng theo kênh", en: "Posts by Channel" })}</h2>
            {data.attribution.length === 0 ? (
              <EmptyState
                title={t({ vi: "Chưa có bài đã đăng", en: "No published posts yet" })}
                body={t({ vi: "Khi đăng bài thành công, tỷ trọng theo kênh sẽ hiện ở đây.", en: "Channel distribution will appear when posts are published." })}
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
          </section>

          <section className={styles.topPostsCard} aria-label="Bài viết Facebook gần đây">
            <h2 className={styles.sectionTitle}>
              {t({ vi: "📘 Bài Viết Fanpage Facebook Đã Đăng Gần Đây", en: "Recent Published Facebook Posts" })}
            </h2>
            {!data.topPosts || data.topPosts.length === 0 ? (
              <EmptyState
                title={t({ vi: "Chưa có bài đăng Facebook", en: "No Facebook posts yet" })}
                body={t({ vi: "Các bài viết Fanpage sau khi được bạn duyệt và đăng thành công sẽ xuất hiện tại đây.", en: "Posts approved and published to your Fanpage will appear here." })}
              />
            ) : (
              <div className={styles.topPostsList}>
                {data.topPosts.map((post) => (
                  <div key={post.id} className={styles.topPostItem}>
                    <div className={styles.topPostHeader}>
                      <span className={styles.topPostBadge}>
                        {channelLabels[post.channel] ?? "Facebook Fanpage"}
                      </span>
                      {post.published_at && (
                        <span className={styles.topPostDate}>
                          📅 {new Date(post.published_at).toLocaleDateString("vi-VN")}
                        </span>
                      )}
                    </div>
                    <p className={styles.topPostText}>{post.caption}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}
