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
 * Thu gọn được, và **mặc định thu gọn**: người mở app mỗi ngày là nhân viên, và
 * họ tới đây để làm việc chứ không để đọc báo cáo. Chủ bấm mở ra khi cần.
 */

import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "@/lib/i18n/language-context";
import { fetchBrief, formatMinutes, type MorningBrief as Brief } from "./queue.api";
import styles from "./morning-brief.module.css";

export function MorningBrief() {
  const { t } = useLanguage();
  const [brief, setBrief] = useState<Brief | null>(null);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    const result = await fetchBrief();
    if (result.ok) setBrief(result.data);
    // Bản tin hỏng thì **im lặng**: nó là phần phụ trợ trên hàng đợi, và một
    // banner lỗi ở đây sẽ che mất việc cần làm — thứ người dùng vào đây để làm.
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Payload lạ cũng xử như không có bản tin, **không** để nó ném giữa lúc render:
  // `MorningBrief` nằm bên trong màn hàng đợi, nên một lỗi ở đây sẽ đánh sập cả
  // danh sách việc — thứ người dùng vào đây để làm.
  if (!brief?.activity || !brief.time_saved_actions) return null;

  const { activity, time_saved_minutes: saved, calendar_gaps: gaps } = brief;
  const quiet =
    activity.published === 0 &&
    activity.inbox_received === 0 &&
    activity.replies_sent === 0 &&
    activity.publish_failed === 0;

  return (
    <section className={styles.card} aria-label={t("Bản tin 24 giờ qua")}>
      <button
        type="button"
        className={styles.summary}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span className={styles.summaryText}>
          {quiet
            ? t("24 giờ qua không có hoạt động nào")
            : `24 giờ qua: ${activity.published} bài đã lên kênh · ${activity.inbox_received} tin khách · ${activity.replies_sent} đã trả lời`}
          {activity.publish_failed > 0 ? (
            <strong className={styles.failed}> · {activity.publish_failed} bài lỗi</strong>
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
          <div className={styles.block}>
            <p className={styles.blockTitle}>
              {t("Havi làm thay bạn")} {formatMinutes(saved)} {t("trong 24 giờ qua")}
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
