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

function attributionPercent(item: ChannelAttribution): number {
  return Math.max(0, Math.min(100, Math.round(item.share * 100)));
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
      {
        label: t("dashboard.publishedPosts", "Bài đã đăng"),
        value: String(reportsData.summary.published_posts),
        change: reportsData.summary.change_vs_previous_period?.published_posts || 0,
      },
      {
        label: t({ vi: "Hội thoại đã nhận", en: "Inbox items received" }),
        value: String(reportsData.summary.inbox_items),
        change: reportsData.summary.change_vs_previous_period?.inbox_items || 0,
      },
      {
        label: t({ vi: "Phản hồi đã gửi", en: "Replies sent" }),
        value: String(reportsData.summary.replies_sent),
        change: reportsData.summary.change_vs_previous_period?.replies_sent || 0,
      },
      {
        label: t({ vi: "Lượt đăng thất bại", en: "Failed publishes" }),
        value: String(reportsData.summary.failed_posts),
        change: reportsData.summary.change_vs_previous_period?.failed_posts || 0,
      },
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
          {t("reports.subtitle", "Theo dõi tình trạng xuất bản và hội thoại theo dữ liệu nền tảng")}
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
          {/*
            Chỉ hiện những gì Havi THẬT SỰ làm và đếm được.

            Bản trước hiện ba con số: "~N giờ tiết kiệm" (nhân 1,5 giờ mỗi bài
            — hệ số bịa, và `Math.max(1, …)` khiến nó hiện "~1 giờ" ngay cả khi
            chưa đăng bài nào), "< 10 giây phản hồi Messenger" và "100% đúng
            giọng thương hiệu" — cả hai hard-code, không đo gì.

            Một chủ tiệm mở báo cáo ngày đầu, thấy thành tích mình chưa hề có,
            thì mọi con số còn lại cũng mất giá trị theo.
          */}
          {data.summary.published_posts > 0 || data.summary.inbox_items > 0 ? (
            <section className={styles.peaceOfMindCard} aria-label="Việc Havi đã làm">
              <div className={styles.peaceOfMindBadge}>VIỆC HAVI ĐÃ LÀM</div>
              <div className={styles.peaceOfMindGrid}>
                <div className={styles.peaceOfMindItem}>
                  <span className={styles.peaceOfMindVal}>{data.summary.published_posts}</span>
                  <span className={styles.peaceOfMindLbl}>Bài đã lên Trang</span>
                </div>
                <div className={styles.peaceOfMindItem}>
                  <span className={styles.peaceOfMindVal}>{data.summary.inbox_items}</span>
                  <span className={styles.peaceOfMindLbl}>Hội thoại đã nhận</span>
                </div>
              </div>
            </section>
          ) : (
            <section className={styles.peaceOfMindCard} aria-label="Chưa đủ dữ liệu">
              <div className={styles.peaceOfMindBadge}>CHƯA ĐỦ DỮ LIỆU</div>
              <p className={styles.emptyHint}>
                Báo cáo hiện lên sau khi có bài đầu tiên được đăng hoặc khách đầu
                tiên nhắn tin. Havi không hiện số liệu mẫu.
              </p>
            </section>
          )}

          <section className={styles.statsGrid} aria-label={t("dashboard.quickStats", "Thống kê nhanh")}>
            {getStatCards(data).map((card) => {
              const isPositive = card.change > 0;
              const isZero = card.change === 0;
              return (
                <div key={card.label} className={styles.statCard}>
                  <div className={styles.statValueRow}>
                    <div className={styles.statValue}>{card.value}</div>
                    {!isZero && (
                      <div className={`${styles.statChange} ${isPositive ? styles.changePositive : styles.changeNegative}`}>
                        {isPositive ? "↑" : "↓"} {Math.abs(card.change)}%
                      </div>
                    )}
                  </div>
                  <div className={styles.statLabel}>{card.label}</div>
                </div>
              );
            })}
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

          <section className={styles.failedPostsCard} aria-label="Bài đăng gặp sự cố">
            <h2 className={styles.sectionTitle}>
              {t({ vi: "🚨 Bài Đăng Gặp Sự Cố", en: "Failed Posts" })}
            </h2>
            {!data.failedPosts || data.failedPosts.length === 0 ? (
              <EmptyState
                title={t({ vi: "Không có sự cố nào", en: "No failures" })}
                body={t({ vi: "Tuyệt vời! Không có bài viết nào bị lỗi trong kỳ báo cáo này.", en: "Great! No posts failed during this reporting period." })}
              />
            ) : (
              <div className={styles.failedPostsList}>
                {data.failedPosts.map((post) => (
                  <div key={post.id} className={styles.failedPostItem}>
                    <div className={styles.failedPostHeader}>
                      <span className={styles.failedPostBadge}>
                        {channelLabels[post.channel] ?? post.channel}
                      </span>
                      {post.scheduled_at && (
                        <span className={styles.failedPostDate}>
                          📅 {new Date(post.scheduled_at).toLocaleDateString("vi-VN")}
                        </span>
                      )}
                    </div>
                    <p className={styles.failedPostText}>{post.caption}</p>
                    <div className={styles.failedPostReason}>
                      <strong>{t({ vi: "Lý do: ", en: "Reason: " })}</strong>
                      {post.failure_detail || t({ vi: "Không rõ nguyên nhân.", en: "Unknown reason." })}
                    </div>
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
