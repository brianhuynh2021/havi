"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import { useLanguage, type Translate } from "@/lib/i18n/language-context";
import { fetchResponseMetrics, type ResponseMetrics } from "@/features/queue/queue.api";
import {
  fetchReports,
  type ChannelAttribution,
  type ReportsData,
} from "./reports.api";
import styles from "./reports.module.css";

// i18n-data: nhãn kênh, `t()` dịch ở chỗ render
const channelLabels: Record<string, string> = {
  facebook_page: "Facebook Page",
  google_business: "Google Maps SEO",
  reels: "Facebook Reels",
  tiktok: "TikTok",
  youtube: "YouTube Shorts",
  email: "Email",
  zalo_oa: "Zalo OA (Lưu trữ)",
};

/** "8 phút", "3 giờ 20 phút" — giây thô không nói được gì cho người đọc. */
function formatWait(seconds: number, t: Translate): string {
  if (seconds < 60) return t("{seconds} giây", { seconds: seconds });
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return t("{minutes} phút", { minutes: minutes });
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? t("{hours} giờ {rest} phút", { hours: hours, rest: rest }) : t("{hours} giờ", { hours: hours });
}

function attributionPercent(item: ChannelAttribution): number {
  return Math.max(0, Math.min(100, Math.round(item.share * 100)));
}

export function ReportsScreen() {
const { t } = useLanguage();
  const [data, setData] = useState<ReportsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [loss, setLoss] = useState<ResponseMetrics | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      // Cửa sổ 30 ngày gần nhất. `waiting_over_*` và `missed_costly` tính theo
      // hiện tại chứ không theo cửa sổ — xem `InboxRepository.response_metrics`.
      const today = new Date();
      const from = new Date(today.getTime() - 29 * 86_400_000);
      const iso = (d: Date) => d.toISOString().slice(0, 10);
      void fetchResponseMetrics(iso(from), iso(today)).then((res) => {
        if (!cancelled && res.ok) setLoss(res.data);
      });

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
        label: t("Bài đã đăng"),
        value: String(reportsData.summary.published_posts),
        change: reportsData.summary.change_vs_previous_period?.published_posts || 0,
      },
      {
        label: t("Hội thoại đã nhận"),
        value: String(reportsData.summary.inbox_items),
        change: reportsData.summary.change_vs_previous_period?.inbox_items || 0,
      },
      {
        label: t("Phản hồi đã gửi"),
        value: String(reportsData.summary.replies_sent),
        change: reportsData.summary.change_vs_previous_period?.replies_sent || 0,
      },
      {
        label: t("Lượt đăng thất bại"),
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
        <h1 className={styles.title}>{t("Báo cáo")}</h1>
        <p className={styles.subtitle}>
          {t("Theo dõi tình trạng xuất bản và hội thoại")}
        </p>
      </header>

      {error ? (
        <ErrorState
          title={t(error)}
          action={
            <Button variant="outline" onClick={() => setReloadKey((key) => key + 1)}>
              {t("Thử lại")}
            </Button>
          }
        />
      ) : loading || !data ? (
        <LoadingState title={t("Đang tải báo cáo…")} />
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
            <section className={styles.peaceOfMindCard} aria-label={t("Việc Havi đã làm")}>
              <div className={styles.peaceOfMindBadge}>{t("VIỆC HAVI ĐÃ LÀM")}</div>
              <div className={styles.peaceOfMindGrid}>
                <div className={styles.peaceOfMindItem}>
                  <span className={styles.peaceOfMindVal}>{data.summary.published_posts}</span>
                  <span className={styles.peaceOfMindLbl}>{t("Bài đã lên Trang")}</span>
                </div>
                <div className={styles.peaceOfMindItem}>
                  <span className={styles.peaceOfMindVal}>{data.summary.inbox_items}</span>
                  <span className={styles.peaceOfMindLbl}>{t("Hội thoại đã nhận")}</span>
                </div>
              </div>
            </section>
          ) : (
            <section className={styles.peaceOfMindCard} aria-label={t("Chưa đủ dữ liệu")}>
              <div className={styles.peaceOfMindBadge}>{t("CHƯA ĐỦ DỮ LIỆU")}</div>
              <p className={styles.emptyHint}>{t(
                "Báo cáo hiện lên sau khi có bài đầu tiên được đăng hoặc khách đầu\n                tiên nhắn tin. Havi không hiện số liệu mẫu."
              )}</p>
            </section>
          )}

          {/*
            Tổn thất tránh được — khối duy nhất trên màn này bán được hàng.

            Bốn con số dưới nó ("bài đã đăng", "hội thoại đã nhận"…) là *đếm hoạt
            động*: chúng nói Havi có chạy, không nói Havi có giá trị. Còn "tuần
            trước bạn sót 12 tin hỏi giá" thì kiểm chứng được, và đó là câu khiến
            người ta gia hạn.

            Cố ý không có chỉ số nào về doanh thu hay khách đến: Havi báo cáo việc
            nó đã làm, kết quả kinh doanh thuộc về doanh nghiệp.
          */}
          {loss ? (
            <section className={styles.statsGrid} aria-label={t("Tổn thất tránh được")}>
              <div className={styles.statCard}>
                <p className={styles.statLabel}>{t("Thời gian trả lời khách")}</p>
                <p className={styles.statValue}>
                  {loss.replied_count > 0 ? formatWait(loss.avg_response_seconds, t) : "—"}
                </p>
                <p className={styles.statDetail}>
                  {loss.replied_count > 0
                    ? t("{replied_count} tin đã trả lời · chậm nhất {value}", { replied_count: loss.replied_count, value: formatWait(loss.p95_response_seconds, t) })
                    : t("Chưa có tin nào được trả lời trong kỳ")}
                </p>
              </div>
              <div className={styles.statCard}>
                <p className={styles.statLabel}>{t("Đang chờ quá 4 giờ")}</p>
                <p className={styles.statValue}>{loss.waiting_over_4h}</p>
                <p className={styles.statDetail}>
                  {loss.waiting_over_1h} {t("tin chờ quá 1 giờ")}
                </p>
              </div>
              <div className={styles.statCard}>
                <p className={styles.statLabel}>{t("Tin hỏi giá bị bỏ sót")}</p>
                <p className={styles.statValue}>{loss.missed_costly}</p>
                <p className={styles.statDetail}>
                  {t("Hỏi giá, đặt lịch hoặc khiếu nại chưa từng được trả lời sau hơn một ngày")}
                </p>
              </div>
            </section>
          ) : null}

          <section className={styles.statsGrid} aria-label={t("Thống kê nhanh")}>
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

          <section className={styles.chartCard} aria-label={t("Bài đăng theo tuần")}>
            <h2 className={styles.sectionTitle}>{t("Bài đăng theo tuần")}</h2>
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

          <section className={styles.attributionCard} aria-label={t("Bài đã đăng theo kênh")}>
            <h2 className={styles.sectionTitle}>{t("Bài đã đăng theo kênh")}</h2>
            {data.attribution.length === 0 ? (
              <EmptyState
                title={t("Chưa có bài đã đăng")}
                body={t("Khi đăng bài thành công, tỷ trọng theo kênh sẽ hiện ở đây.")}
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

          <section className={styles.topPostsCard} aria-label={t("Bài viết Facebook gần đây")}>
            <h2 className={styles.sectionTitle}>
              {t("📘 Bài Viết Fanpage Facebook Đã Đăng Gần Đây")}
            </h2>
            {!data.topPosts || data.topPosts.length === 0 ? (
              <EmptyState
                title={t("Chưa có bài đăng Facebook")}
                body={t("Các bài viết Fanpage sau khi được bạn duyệt và đăng thành công sẽ xuất hiện tại đây.")}
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

          <section className={styles.failedPostsCard} aria-label={t("Bài đăng gặp sự cố")}>
            <h2 className={styles.sectionTitle}>
              {t("🚨 Bài Đăng Gặp Sự Cố")}
            </h2>
            {!data.failedPosts || data.failedPosts.length === 0 ? (
              <EmptyState
                title={t("Không có sự cố nào")}
                body={t("Tuyệt vời! Không có bài viết nào bị lỗi trong kỳ báo cáo này.")}
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
                      <strong>{t("Lý do: ")}</strong>
                      {post.failure_detail || t("Không rõ nguyên nhân.")}
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
