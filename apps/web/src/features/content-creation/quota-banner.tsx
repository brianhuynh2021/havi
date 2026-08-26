"use client";

import { useEffect, useState } from "react";
import { fetchQuota, type TokenQuota } from "./content-creation.api";
import { useLanguage } from "@/lib/i18n/language-context";
import styles from "./quota-banner.module.css";

const vnDateParts = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  day: "2-digit",
  month: "2-digit",
});

function formatVnDate(iso: string): string {
  const parts = vnDateParts.formatToParts(new Date(iso));
  const day = parts.find((p) => p.type === "day")?.value ?? "";
  const month = parts.find((p) => p.type === "month")?.value ?? "";
  return `${day}/${month}`;
}

export function QuotaBanner({ reloadKey = 0 }: { reloadKey?: number }) {
  const [quota, setQuota] = useState<TokenQuota | null>(null);
  const { t } = useLanguage();

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const result = await fetchQuota();
      if (cancelled) return;
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
        <p className={styles.title}>
          {t("Hết lượt tạo bài tháng này")}
        </p>
        <p className={styles.body}>
          {t("Lượt tạo bài sẽ mở lại ngày {date}. Bài đã duyệt vẫn đăng đúng lịch bình thường.", {
            date: resets,
          })}
        </p>
      </div>
    );
  }

  const postsLeft = Math.max(1, Math.floor(quota.remaining / 4000));
  return (
    <div className={`${styles.banner} ${styles.warning}`} role="status">
      <p className={styles.title}>
        {t("Còn khoảng {posts} bài trong tháng này", { posts: postsLeft })}
      </p>
      <p className={styles.body}>
        {t("Lượt tạo bài sẽ mở lại ngày {date}. Havi báo trước để bạn chủ động lên lịch đăng.", {
          date: resets,
        })}
      </p>
    </div>
  );
}

