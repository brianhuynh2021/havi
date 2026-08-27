"use client";

/**
 * Bản tin buổi sáng — **màn của chủ**, đứng trên hàng đợi của nhân viên.
 *
 * Hai người, hai nhịp: nhân viên trực kênh mở Havi mỗi ngày để làm hàng đợi; chủ
 * mở mỗi tuần để biết chuyện gì đã xảy ra và Havi có đáng tiền không. Gộp cả hai
 * vào một danh sách là bắt chủ đọc 40 dòng để tìm 4 câu.
 *
 * Mọi con số ở đây đếm từ dữ liệu Havi đã sở hữu, **không gọi LLM**. Nên nó không
 * nói được "doanh thu từ social tăng 12%" hay "engagement Instagram giảm 18%" —
 * và đó là chủ ý: Havi không có dữ liệu đơn hàng, chưa có quyền đọc insights.
 * Thiếu thì để trống, không đoán.
 *
 * Thu gọn được, nhưng mặc định mở để North Star "Time Havi Saved" không bị giấu
 * sau một thao tác. Khối này vẫn đứng trên hàng đợi và giữ chiều cao ngắn.
 */

import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "@/lib/i18n/language-context";
import { fetchBrief, formatMinutes, type MorningBrief as Brief } from "./queue.api";
import styles from "./morning-brief.module.css";

export function MorningBrief() {
  const { t } = useLanguage();
  const [brief, setBrief] = useState<Brief | null>(null);
  const [open, setOpen] = useState(true);

  const load = useCallback(async () => {
    const result = await fetchBrief();
    if (result.ok) setBrief(result.data);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (!brief?.activity || !brief.time_saved_actions) return null;

  const { activity, time_saved_minutes: saved, calendar_gaps: gaps } = brief;
  const silent = brief.silent_channels ?? [];
  const quiet =
    activity.published === 0 &&
    activity.inbox_received === 0 &&
    activity.replies_sent === 0 &&
    activity.publish_failed === 0;

  return (
    <section className={styles.card} aria-label={t("Bản tin vận hành 24 giờ qua")}>
      <button
        type="button"
        className={styles.summary}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span className={styles.summaryText}>
          ✨ {t("Bản tin Havi:")} {quiet
            ? t("24 giờ qua chưa ghi nhận hoạt động nào.")
            : t("24 giờ qua có {published} bài đã đăng · {inbox_received} tin khách · {replies_sent} tin đã xử lý", { published: activity.published, inbox_received: activity.inbox_received, replies_sent: activity.replies_sent })}
          {activity.publish_failed > 0 ? (
            <strong className={styles.failed}> · {activity.publish_failed} bài đăng lỗi</strong>
          ) : null}
        </span>
        <span className={styles.chevron} aria-hidden="true">
          {open ? "▲" : "▼"}
        </span>
      </button>

      {open ? (
        <div className={styles.body}>
          {/* Thời gian tiết kiệm — kèm phép tính, luôn luôn.
              Con số tổng mà ẩn giả định đi thì nó là quảng cáo, không phải số
              liệu. Khách thấy được phép tính thì họ tự kiểm và tin. */}
          <div className={`${styles.block} ${styles.savedBlock}`}>
            <p className={`${styles.blockTitle} ${styles.savedTitle}`}>
              🌟 {t("Havi đã tiết kiệm {time} trong 24 giờ qua", { time: formatMinutes(saved) })}
            </p>
            <ul className={styles.calc}>
              {brief.time_saved_actions.map((action) => (
                <li key={action.action} className={styles.calcRow}>
                  <span>{action.action}</span>
                  <span className={styles.calcDetail}>
                    {action.count} × {action.minutes_each} {t("phút")} ={" "}
                    {formatMinutes(action.minutes_total)}
                  </span>
                </li>
              ))}
            </ul>
            <p className={styles.assumption}>
              {t(
                "Chỉ đếm việc Havi thật sự đã làm, nhân với giả định thời gian ở trên. Không đếm những thứ không đo được.",
              )}
            </p>
          </div>

          {brief.attention_total > 0 ? (
            <div className={styles.block}>
              <p className={styles.blockTitle}>
                {brief.attention_total} {t("việc đang chờ")}
                {brief.attention_costly > 0 ? (
                  <span className={styles.costly}>
                    {" "}
                    — {brief.attention_costly} {t("việc bỏ sót là mất khách")}
                  </span>
                ) : null}
              </p>
              <p className={styles.blockHint}>{t("Danh sách đầy đủ ở ngay dưới.")}</p>
            </div>
          ) : null}

          {/* Kênh im lặng — quá khứ; chỗ trống lịch ngay dưới — tương lai.
              Đọc theo thứ tự đó thì hai mục thành một câu: kênh nào đang bị bỏ,
              và tuần tới còn chỗ nào để lấp lại.

              Chỉ nói đúng cái Havi đếm được: bao lâu rồi chưa đăng. Không nói
              "trang đang nguội" hay "reach sẽ giảm" — Havi không đo reach. */}
          {silent.length > 0 ? (
            <div className={styles.block}>
              <p className={styles.blockTitle}>
                {silent.length} {t("kênh đang mở nhưng lâu chưa đăng")}
              </p>
              <ul className={styles.calc}>
                {silent.map((channel) => (
                  <li key={channel.channel} className={styles.calcRow}>
                    <span>{channel.label}</span>
                    <span className={styles.calcDetail}>
                      {channel.ever_published
                        ? t("{days} ngày chưa đăng", { days: channel.days })
                        : t("nối {days} ngày, chưa đăng bài nào", { days: channel.days })}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {gaps.length > 0 ? (
            <div className={styles.block}>
              <p className={styles.blockTitle}>
                {gaps.length} {t("ngày tới chưa có bài nào xếp lịch")}
              </p>
              <div className={styles.gapRow}>
                {gaps.map((gap) => (
                  <span key={gap.date} className={styles.gapChip}>
                    {gap.weekday}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className={styles.block}>
              <p className={styles.blockTitle}>{t("Bảy ngày tới đã có bài mỗi ngày")}</p>
            </div>
          )}
        </div>
      ) : null}
    </section>
  );
}
