"use client";

import { useEffect, useState } from "react";
import { fetchQuota, type TokenQuota } from "./content-creation.api";
import styles from "./quota-banner.module.css";

const vnDateParts = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  day: "2-digit",
  month: "2-digit",
});

/** `dd/MM` theo giờ VN.
 *
 * Ghép tay từ `formatToParts` thay vì dùng chuỗi `format()` trả về: locale
 * `vi-VN` cho ra `01-09` (gạch ngang), trong khi ROADMAP §4 chốt hiển thị ngày
 * kiểu `dd/MM/yyyy`. Múi giờ vẫn để `Intl` lo — đó mới là phần dễ sai.
 */
function formatVnDate(iso: string): string {
  const parts = vnDateParts.formatToParts(new Date(iso));
  const day = parts.find((p) => p.type === "day")?.value ?? "";
  const month = parts.find((p) => p.type === "month")?.value ?? "";
  return `${day}/${month}`;
}

/**
 * Cảnh báo quota — hiện **trước** khi chủ tiệm bị chặn.
 *
 * Chỉ hiện khi gần hết (≥80%) hoặc đã hết. Còn nhiều thì ẩn hẳn: một thanh
 * "đã dùng 3%" thường trực chỉ làm chủ tiệm lo về thứ không cần lo, và chiếm chỗ
 * của ô nạp liệu.
 *
 * Đo bằng *số bài* chứ không bằng token trong câu chữ: chủ tiệm spa không biết
 * "480.000 token" là nhiều hay ít, nhưng biết "còn khoảng 4 bài" nghĩa là gì.
 */
export function QuotaBanner({ reloadKey = 0 }: { reloadKey?: number }) {
  const [quota, setQuota] = useState<TokenQuota | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const result = await fetchQuota();
      if (cancelled) return;
      // Hỏng thì ẩn banner, không hiện lỗi: đây là thông tin phụ trợ, không phải
      // thứ chặn chủ tiệm làm việc.
      if (result.ok) setQuota(result.data);
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  if (!quota) return null;
  if (!quota.exceeded && !quota.near_limit) return null;

  const resets = formatVnDate(quota.resets_at);

  if (quota.exceeded) {
    return (
      <div className={`${styles.banner} ${styles.blocked}`} role="alert">
        <p className={styles.title}>Hết lượt tạo bài tháng này</p>
        <p className={styles.body}>
          Quota mở lại ngày {resets}. Bài đã duyệt vẫn đăng đúng lịch bình thường
          — chỉ tạm thời chưa tạo bài mới được. Cần thêm ngay thì nhắn Havi để
          nâng gói.
        </p>
      </div>
    );
  }

  // ~4.000 token một bài (prompt + brand profile + 3 draft). Số nhân ở đây là
  // ước lượng để chủ tiệm hình dung, không phải cam kết — nói "khoảng".
  const postsLeft = Math.max(1, Math.floor(quota.remaining / 4000));
  return (
    <div className={`${styles.banner} ${styles.warning}`} role="status">
      <p className={styles.title}>Còn khoảng {postsLeft} bài trong tháng này</p>
      <p className={styles.body}>
        Quota mở lại ngày {resets}. Chị cứ dùng bình thường — Havi báo trước để
        không bị kẹt giữa lúc cần đăng bài.
      </p>
    </div>
  );
}
