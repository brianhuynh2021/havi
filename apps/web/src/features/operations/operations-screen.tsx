"use client";

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

const vnDateTime = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function metricCards(data: OperationsMetrics) {
  return [
    { label: "Event", value: number(data.event_count), detail: `${number(data.error_count)} lỗi` },
    { label: "Tỷ lệ lỗi", value: percent(data.error_rate), detail: "Theo event log" },
    { label: "Token", value: number(data.tokens_total), detail: `${number(data.tokens_in)} in / ${number(data.tokens_out)} out` },
    { label: "P95 latency", value: `${number(data.p95_duration_ms)}ms`, detail: `Avg ${number(data.avg_duration_ms)}ms` },
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

  return (
    <>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Internal pilot</p>
          <h1 className={styles.title}>Vận hành</h1>
        </div>
        <p className={styles.subtitle}>
          Debug job, token và publish health bằng dữ liệu aggregate trong workspace.
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
        <LoadingState title="Đang tải vận hành…" />
      ) : (
        <>
          <section className={styles.windowNote}>
            Cửa sổ: {vnDateTime.format(new Date(data.window_start))} -{" "}
            {vnDateTime.format(new Date(data.window_end))} giờ VN
          </section>

          {hasNoOperationalData(data) ? (
            <EmptyState
              title="Chưa có dữ liệu vận hành"
              body="Khi worker tạo nội dung hoặc publish job chạy, số liệu debug sẽ hiện ở đây."
            />
          ) : null}

          <section className={styles.statsGrid} aria-label="Số liệu job nội bộ">
            {metricCards(data).map((item) => (
              <div key={item.label} className={styles.statCard}>
                <p className={styles.statLabel}>{item.label}</p>
                <p className={styles.statValue}>{item.value}</p>
                <p className={styles.statDetail}>{item.detail}</p>
              </div>
            ))}
          </section>

          <section className={styles.splitGrid}>
            <article className={styles.panel}>
              <h2 className={styles.panelTitle}>Publish health</h2>
              <div className={styles.publishGrid}>
                <div>
                  <p className={styles.miniLabel}>Tổng job</p>
                  <p className={styles.miniValue}>{number(data.publish.total)}</p>
                </div>
                <div>
                  <p className={styles.miniLabel}>Thành công</p>
                  <p className={styles.miniValue}>{number(data.publish.succeeded)}</p>
                </div>
                <div>
                  <p className={styles.miniLabel}>Dead-letter</p>
                  <p className={styles.miniValue}>{number(data.publish.dead_letter)}</p>
                </div>
              </div>
              <div className={styles.rateRows}>
                <div className={styles.rateRow}>
                  <span>Success rate</span>
                  <strong>{percent(data.publish.success_rate)}</strong>
                </div>
                <div className={styles.rateRow}>
                  <span>Dead-letter rate</span>
                  <strong>{percent(data.publish.dead_letter_rate)}</strong>
                </div>
              </div>
            </article>

            <article className={styles.panel}>
              <h2 className={styles.panelTitle}>Provider breakdown</h2>
              {data.providers.length === 0 ? (
                <EmptyState
                  title="Chưa có provider nào"
                  body="Provider sẽ xuất hiện sau khi LLM hoặc publisher ghi event."
                />
              ) : (
                <div className={styles.providerList}>
                  {data.providers.map((provider) => (
                    <div key={provider.provider} className={styles.providerRow}>
                      <span className={styles.providerName}>{provider.provider}</span>
                      <span>{number(provider.event_count)} event</span>
                      <span>{number(provider.tokens_total)} token</span>
                      <strong>{providerErrorRate(provider)} lỗi</strong>
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
