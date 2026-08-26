"use client";

/**
 * Chọn cách đưa một loạt nội dung lên Trang: đăng ngay, hay rải ra nhiều ngày.
 *
 * Dùng chung cho cả bài viết lẫn video — đó là điểm hai nhánh gặp lại nhau. Chủ
 * tiệm ngồi một buổi chuẩn bị nội dung cả tuần thì việc còn lại giống hệt nhau
 * dù đó là bài chữ hay clip: xếp thứ tự, chọn mật độ, xem trước ngày giờ.
 *
 * Bảng xem trước không phải trang trí. Không có nó, "rải lịch" là một lời hứa
 * trừu tượng và chủ tiệm chỉ biết Havi đã chọn giờ nào sau khi bài đã lên.
 */

import { useLanguage } from "@/lib/i18n/language-context";
import { Button } from "@/components/ui/button";
import { PERMISSIONS, usePermissions } from "@/lib/auth/use-permissions";
import styles from "./content-creation.module.css";

/**
 * Khung giờ vàng — phải khớp `GOLDEN_HOURS` ở
 * `apps/backend/domain/policies/scheduling.py`. Backend mới là nơi quyết định
 * giờ thật; bảng này chỉ để xem trước, nên lệch nhau là hiện sai chứ không đăng
 * sai. Đổi một bên thì đổi cả hai.
 */
const GOLDEN_HOURS = [8, 12, 20];

const VN_TIME_ZONE = "Asia/Ho_Chi_Minh";

/** Tên vai bằng tiếng Việt — `marketer` không nói gì với người đang bị chặn. */
const ROLE_NAMES: Record<string, string> = {
  owner: "Chủ workspace",
  marketer: "Người soạn",
  reviewer: "Người duyệt",
  sales: "Trực hội thoại",
};

export type SchedulePlan = { publishNow: boolean; postsPerDay: number };

/**
 * Dựng lại lịch backend sẽ cấp, để hiện trước khi bấm.
 *
 * Cùng luật với `spread_over_golden_hours`: ngày đầu bỏ khung đã trôi qua, mỗi
 * ngày lấy `postsPerDay` khung đầu tiên, hết thì sang ngày kế.
 */
export function previewSchedule(
  count: number,
  postsPerDay: number,
  now: Date = new Date(),
): Date[] {
  if (count <= 0) return [];
  const perDay = Math.max(1, Math.min(postsPerDay, GOLDEN_HOURS.length));
  const slots: Date[] = [];

  for (let dayOffset = 0; slots.length < count; dayOffset += 1) {
    for (const hour of GOLDEN_HOURS.slice(0, perDay)) {
      const candidate = new Date(now);
      candidate.setDate(candidate.getDate() + dayOffset);
      candidate.setHours(hour, 0, 0, 0);
      if (dayOffset === 0 && candidate <= now) continue;
      slots.push(candidate);
      if (slots.length === count) break;
    }
  }
  return slots;
}

const dayFormatter = new Intl.DateTimeFormat("vi-VN", {
  timeZone: VN_TIME_ZONE,
  weekday: "short",
  day: "2-digit",
  month: "2-digit",
});

const timeFormatter = new Intl.DateTimeFormat("vi-VN", {
  timeZone: VN_TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

type SchedulePickerProps = {
  /** Tiêu đề của từng mục, đúng thứ tự sẽ lên bài. */
  labels: string[];
  plan: SchedulePlan;
  onPlanChange: (plan: SchedulePlan) => void;
  onConfirm: () => void;
  busy: boolean;
  /** "bài" hoặc "video" — chỉ để câu chữ đọc tự nhiên. */
  noun: string;
};

export function SchedulePicker({
  labels,
  plan,
  onPlanChange,
  onConfirm,
  busy,
  noun,
}: SchedulePickerProps) {
  const {
    t
  } = useLanguage();

  const { can, role } = usePermissions();
  const mayApprove = can(PERMISSIONS.approveContent);

  const count = labels.length;
  const slots = plan.publishNow ? [] : previewSchedule(count, plan.postsPerDay);
  const lastDay = slots.length ? slots[slots.length - 1] : null;

  // Vai không được duyệt vẫn **thấy toàn bộ bảng xem trước** — họ cần biết nội
  // dung sẽ lên lúc nào để bàn với người duyệt. Chỉ nút bấm biến mất.
  if (!mayApprove) {
    return (
      <section className={styles.scheduleCard} aria-labelledby="schedule-title">
        <h3 id="schedule-title" className={styles.scheduleTitle}>
          {count} {noun}{" "}{t("này đang chờ duyệt")}</h3>
        <p className={styles.approveBlocked}>{t("Vai của bạn")}{role ? ` (${ROLE_NAMES[role] ?? role})` : ""}{t(
          "soạn được nhưng\n          không duyệt được. Nhờ Người duyệt hoặc Chủ workspace bấm duyệt giúp —\n          đó là điểm khiến bước duyệt có nghĩa."
        )}</p>
        <ol className={styles.schedulePreview}>
          {labels.map((label, index) => (
            <li key={`${label}-${index}`} className={styles.scheduleRow}>
              <span className={styles.scheduleWhen}>—</span>
              <span className={styles.scheduleWhat}>{label}</span>
            </li>
          ))}
        </ol>
      </section>
    );
  }

  return (
    <section className={styles.scheduleCard} aria-labelledby="schedule-title">
      <h3 id="schedule-title" className={styles.scheduleTitle}>{t("Đưa")}{" "}{count} {noun}{" "}{t("này lên Trang thế nào?")}</h3>

      <div className={styles.scheduleModes} role="group" aria-label={t("Cách đăng")}>
        <button
          type="button"
          aria-pressed={!plan.publishNow}
          className={`${styles.scheduleMode} ${!plan.publishNow ? styles.scheduleModeActive : ""}`}
          onClick={() => onPlanChange({ ...plan, publishNow: false })}
        >
          <strong>{t("Rải nhiều ngày")}</strong>
          <small>{t("Mỗi ngày một câu chuyện, đăng vào khung giờ đông người xem.")}</small>
        </button>
        <button
          type="button"
          aria-pressed={plan.publishNow}
          className={`${styles.scheduleMode} ${plan.publishNow ? styles.scheduleModeActive : ""}`}
          onClick={() => onPlanChange({ ...plan, publishNow: true })}
        >
          <strong>{t("Đăng hết ngay")}</strong>
          <small>{t("Tất cả lên Trang trong vài phút tới.")}</small>
        </button>
      </div>

      {plan.publishNow ? (
        count > 1 ? (
          <p className={styles.scheduleWarning} role="status">
            {count} {noun}{t(
            "sẽ lên Trang gần như cùng lúc. Người theo dõi thường\n            thấy điều này giống spam hơn là chăm chỉ."
          )}</p>
        ) : null
      ) : (
        <>
          <div className={styles.densityRow}>
            <span className={styles.densityLabel}>{t("Mật độ")}</span>
            {[1, 2, 3].map((perDay) => (
              <button
                key={perDay}
                type="button"
                aria-pressed={plan.postsPerDay === perDay}
                className={`${styles.densityChip} ${
                  plan.postsPerDay === perDay ? styles.densityChipActive : ""
                }`}
                onClick={() => onPlanChange({ ...plan, postsPerDay: perDay })}
              >
                {perDay} {noun}{t("/ngày")}</button>
            ))}
          </div>

          <ol className={styles.schedulePreview}>
            {labels.map((label, index) => {
              const slot = slots[index];
              return (
                <li key={`${label}-${index}`} className={styles.scheduleRow}>
                  <span className={styles.scheduleWhen}>
                    {slot ? (
                      <>
                        <b>{dayFormatter.format(slot)}</b> {timeFormatter.format(slot)}
                      </>
                    ) : (
                      "—"
                    )}
                  </span>
                  <span className={styles.scheduleWhat}>{label}</span>
                </li>
              );
            })}
          </ol>

          {lastDay ? (
            <p className={styles.scheduleFootnote}>{t("Kín nội dung tới")}{" "}{dayFormatter.format(lastDay)}{t(
              ". Sửa hoặc đổi giờ\n              từng bài ở mục Lịch đăng bất cứ lúc nào trước giờ lên."
            )}</p>
          ) : null}
        </>
      )}

      <Button variant="primary" scale="large" onClick={onConfirm} disabled={busy || !count}>
        {busy
          ? "Đang xử lý…"
          : plan.publishNow
            ? `Duyệt & đăng ${count} ${noun} ngay`
            : `Duyệt & xếp lịch ${count} ${noun}`}
      </Button>
    </section>
  );
}
