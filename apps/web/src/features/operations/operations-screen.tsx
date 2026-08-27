"use client";
import { useLanguage, type Translate } from "@/lib/i18n/language-context";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/state-views";
import {
  fetchOperationsMetrics,
  type OperationsMetrics,
  type OperationsProviderMetric,
} from "./operations.api";
import styles from "./operations.module.css";

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function number(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(value);
}

function vnd(value: number, t: Translate): string {
  return t("{value}đ", { value: new Intl.NumberFormat("vi-VN").format(value) });
}

const dayOnly = new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });

/**
 * Ngày của bảng giá, hoặc `null` nếu backend không gửi được ngày dùng được.
 *
 * `Intl.format` **ném RangeError** với Invalid Date, và nó ném ở giữa lúc render
 * nên cả màn trắng — một chú thích nhỏ dưới khối chi phí đánh sập trang debug,
 * đúng lúc người ta mở trang debug ra để xem có gì hỏng.
 */
function pricingDay(value: string | null | undefined): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : dayOnly.format(parsed);
}

const vnDateTime = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function metricCards(data: OperationsMetrics, t: Translate) {
  const slowThresholdSeconds = Math.round(data.slow_content_generation_threshold_ms / 1000);
  return [
    { label: t("Sự kiện"), value: number(data.event_count), detail: t("{value} lỗi trong nhật ký", { value: number(data.error_count) }) },
    { label: t("Tỷ lệ lỗi"), value: percent(data.error_rate), detail: t("Theo nhật ký sự kiện") },
    { label: t("Token AI"), value: number(data.tokens_total), detail: t("{input} vào / {output} ra", { input: number(data.tokens_in), output: number(data.tokens_out) }) },
    { label: t("Độ trễ P95"), value: `${number(data.p95_duration_ms)}ms`, detail: t("Trung bình {value}ms", { value: number(data.avg_duration_ms) }) },
    {
      label: t("Tạo bài chậm"),
      value: number(data.slow_content_generation_count),
      detail: t("{count}/{total} lượt quá {seconds} giây · P95 {p95}ms", {
        count: number(data.slow_content_generation_count),
        total: number(data.content_generation_count),
        seconds: slowThresholdSeconds,
        p95: number(data.content_generation_p95_ms),
      }),
    },
  ];
}

function providerErrorRate(provider: OperationsProviderMetric): string {
  if (provider.event_count === 0) return "0%";
  return percent(provider.error_count / provider.event_count);
}

function hasNoOperationalData(data: OperationsMetrics): boolean {
  return (
    data.event_count === 0 &&
    data.publish.total === 0 &&
    data.tokens_total === 0 &&
    data.providers.length === 0
  );
}

export function OperationsScreen() {
  const {
    t
  } = useLanguage();

  const [data, setData] = useState<OperationsMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      const result = await fetchOperationsMetrics();
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

  // Tính một lần: gọi `pricingDay()` hai lần thì TypeScript không nối được kết
  // quả của lần kiểm tra với lần dùng, và `null` lọt vào chỗ chèn giá trị.
  const asOfDay = data ? pricingDay(data.pricing_as_of) : null;

  return (
    <>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>{t("Thử nghiệm nội bộ")}</p>
          <h1 className={styles.title}>{t("Vận hành")}</h1>
        </div>
        <p className={styles.subtitle}>{t(
          "Theo dõi tác vụ, token và tình trạng xuất bản bằng số liệu tổng hợp của không gian làm việc."
        )}</p>
      </header>

      {error ? (
        <ErrorState
          title={t(error)}
          action={
            <Button variant="outline" onClick={() => setReloadKey((key) => key + 1)}>{t("Thử lại")}</Button>
          }
        />
      ) : loading || !data ? (
        <LoadingState title={t("Đang tải vận hành…")} />
      ) : (
        <>
          <section className={styles.windowNote}>{t("Cửa sổ:")}{" "}{vnDateTime.format(new Date(data.window_start))} -{" "}
            {vnDateTime.format(new Date(data.window_end))}{" "}{t("giờ VN")}</section>

          {hasNoOperationalData(data) ? (
            <EmptyState
              title={t("Chưa có dữ liệu vận hành")}
              body={t(
                "Khi tác vụ tạo nội dung hoặc xuất bản chạy, số liệu vận hành sẽ hiện ở đây."
              )}
            />
          ) : null}

          <section className={styles.statsGrid} aria-label={t("Số liệu tác vụ nội bộ")}>
            {metricCards(data, t).map((item) => (
              <div key={item.label} className={styles.statCard}>
                <p className={styles.statLabel}>{item.label}</p>
                <p className={styles.statValue}>{item.value}</p>
                <p className={styles.statDetail}>{item.detail}</p>
              </div>
            ))}
          </section>

          {/*
            Kinh tế đơn vị — khối duy nhất trên màn này trả lời một câu hỏi kinh
            doanh chứ không phải câu hỏi kỹ thuật: một bài đưa được lên kênh tốn
            bao nhiêu, so với giá gói đang thu.

            Ba con số này đã được API trả về từ trước nhưng không hiện ở đâu cả.
            Một chỉ số tính đúng mà không ai thấy thì bằng không có.
          */}
          <section className={styles.statsGrid} aria-label={t("Kinh tế đơn vị")}>
            <div className={styles.statCard}>
              <p className={styles.statLabel}>{t("Chi phí mỗi bài lên kênh")}</p>
              <p className={styles.statValue}>
                {data.approved_draft_count > 0
                  ? vnd(data.est_cost_per_approved_draft_vnd, t)
                  : "—"}
              </p>
              <p className={styles.statDetail}>
                {data.approved_draft_count > 0
                  ? t("Gồm cả token của nháp đã bị xoá")
                  : t("Chưa có nháp nào được duyệt trong kỳ")}
              </p>
            </div>
            <div className={styles.statCard}>
              <p className={styles.statLabel}>{t("Nháp dùng được")}</p>
              <p className={styles.statValue}>
                {data.generated_draft_count > 0 ? percent(data.draft_usage_rate) : "—"}
              </p>
              <p className={styles.statDetail}>
                {number(data.approved_draft_count)}/{number(data.generated_draft_count)}{" "}
                {t("nháp được duyệt")}
              </p>
            </div>
            <div className={styles.statCard}>
              <p className={styles.statLabel}>{t("Chi phí mỗi lượt tạo bài")}</p>
              <p className={styles.statValue}>
                {data.job_count > 0 ? vnd(data.est_cost_per_job_vnd, t) : "—"}
              </p>
              <p className={styles.statDetail}>
                {number(data.avg_tokens_per_job)} {t("token/lượt")}
              </p>
            </div>
          </section>

          {/* Bảng giá LLM và tỷ giá đều trôi. Một con số tiền không kèm ngày là
              phỏng đoán trông như số liệu, nên nói thẳng nó dựa trên bảng giá
              nào — và cảnh báo khi bảng đó đã quá cũ. */}
          <p className={data.pricing_is_stale ? styles.pricingStale : styles.pricingNote}>
            {data.pricing_is_stale
              ? t("Bảng giá LLM đã quá cũ — mọi con số tiền ở trên chỉ là phỏng đoán. Cập nhật domain/policies/pricing.py.")
              : asOfDay
                ? t("Tiền quy đổi theo bảng giá ngày {date}", { date: asOfDay })
                : t("Không đọc được ngày của bảng giá — coi con số tiền ở trên là phỏng đoán.")}
          </p>

          <section className={styles.splitGrid}>
            <article className={styles.panel}>
              <h2 className={styles.panelTitle}>{t("Tình trạng xuất bản")}</h2>
              <div className={styles.publishGrid}>
                <div>
                  <p className={styles.miniLabel}>{t("Tổng lượt")}</p>
                  <p className={styles.miniValue}>{number(data.publish.total)}</p>
                </div>
                <div>
                  <p className={styles.miniLabel}>{t("Thành công")}</p>
                  <p className={styles.miniValue}>{number(data.publish.succeeded)}</p>
                </div>
                <div>
                  <p className={styles.miniLabel}>{t("Cần xử lý thủ công")}</p>
                  <p className={styles.miniValue}>{number(data.publish.dead_letter)}</p>
                </div>
              </div>
              <div className={styles.rateRows}>
                <div className={styles.rateRow}>
                  <span>{t("Tỷ lệ thành công")}</span>
                  <strong>{percent(data.publish.success_rate)}</strong>
                </div>
                <div className={styles.rateRow}>
                  <span>{t("Tỷ lệ cần xử lý thủ công")}</span>
                  <strong>{percent(data.publish.dead_letter_rate)}</strong>
                </div>
              </div>
            </article>

            <article className={styles.panel}>
              <h2 className={styles.panelTitle}>{t("Theo nhà cung cấp")}</h2>
              {data.providers.length === 0 ? (
                <EmptyState
                  title={t("Chưa có nhà cung cấp nào")}
                  body={t("Nhà cung cấp sẽ xuất hiện sau khi AI hoặc nền tảng ghi nhận một sự kiện.")}
                />
              ) : (
                <div className={styles.providerList}>
                  {data.providers.map((provider) => (
                    <div key={provider.provider} className={styles.providerRow}>
                      <span className={styles.providerName}>{provider.provider}</span>
                      <span>{number(provider.event_count)} {t("sự kiện")}</span>
                      <span>{number(provider.tokens_total)} token</span>
                      <strong>{providerErrorRate(provider)}{" "}{t("lỗi")}</strong>
                    </div>
                  ))}
                </div>
              )}
            </article>
          </section>
        </>
      )}
    </>
  );
}
