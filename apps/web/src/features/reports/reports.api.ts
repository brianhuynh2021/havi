import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import { apiClient } from "@/lib/api-client/client";
import type { components } from "@/lib/api-client/schema";

export type AnalyticsSummary = components["schemas"]["AnalyticsSummary"] & {
  total_revenue_vnd?: number;
};
export type AnalyticsTimeseries = components["schemas"]["AnalyticsTimeseries"];
export type ChannelAttribution = components["schemas"]["ChannelAttribution"];

export type ReportsData = {
  summary: AnalyticsSummary;
  timeseries: AnalyticsTimeseries;
  attribution: ChannelAttribution[];
};

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const vnDate = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Ho_Chi_Minh",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

function toVnDate(value: Date): string {
  return vnDate.format(value);
}

function monthRange(): { start: string; end: string } {
  const now = new Date();
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(now);
  const year = Number(parts.find((part) => part.type === "year")?.value);
  const month = Number(parts.find((part) => part.type === "month")?.value);
  const start = new Date(Date.UTC(year, month - 1, 1));
  const end = new Date(Date.UTC(year, month, 0));
  return { start: toVnDate(start), end: toVnDate(end) };
}

export async function fetchReports(): Promise<Result<ReportsData>> {
  const range = monthRange();
  try {
    const [summary, timeseries, attribution] = await Promise.all([
      apiClient.GET("/analytics/summary", { params: { query: range } }),
      apiClient.GET("/analytics/timeseries", {
        params: { query: { metric: "published_posts", granularity: "week" } },
      }),
      apiClient.GET("/analytics/attribution", { params: { query: range } }),
    ]);

    if (
      summary.error ||
      !summary.data ||
      timeseries.error ||
      !timeseries.data ||
      attribution.error ||
      !attribution.data
    ) {
      return { ok: false, message: "Chưa tải được báo cáo, thử lại giúp chị nhé." };
    }

    return {
      ok: true,
      data: {
        summary: summary.data,
        timeseries: timeseries.data,
        attribution: attribution.data,
      },
    };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
