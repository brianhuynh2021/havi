// i18n-data: hai cơ chế, mỗi cái cho một loại chuỗi.
//
// Câu **hằng** (`"Chưa tải được lịch, thử lại giúp bạn nhé."`) để nguyên tiếng
// Việt: nó chính là khoá, và màn hình hiện nó bằng `t(error)` — tra động vẫn
// đúng vì khoá là câu tiếng Việt. Bọc `t()` ngay tại hằng số cấp module sẽ
// **đóng băng ngôn ngữ lúc import**, đổi ngôn ngữ sau đó không có tác dụng.
//
// Câu **có chèn giá trị** thì phải dịch tại lúc dựng, bằng `translateNow`: sau
// khi đã ghép số vào thì không còn khoá nào để tra ở chỗ render nữa.
//
// Câu do backend trả về không có trong từ điển; `t()` giữ nguyên tiếng Việt.
import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import { apiClient } from "@/lib/api-client/client";
import type { components } from "@/lib/api-client/schema";

export type AnalyticsSummary = components["schemas"]["AnalyticsSummary"];
export type AnalyticsTimeseries = components["schemas"]["AnalyticsTimeseries"];
export type ChannelAttribution = components["schemas"]["ChannelAttribution"];

export type TopPostItem = {
  id: string;
  channel: string;
  caption: string;
  published_at?: string | null;
};

export type FailedPostRecord = components["schemas"]["FailedPostRecord"];

export type ReportsData = {
  summary: AnalyticsSummary;
  timeseries: AnalyticsTimeseries;
  attribution: ChannelAttribution[];
  topPosts: TopPostItem[];
  failedPosts: FailedPostRecord[];
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
    const [summary, timeseries, attribution, calendarData, failedPostsReq] = await Promise.all([
      apiClient.GET("/analytics/summary", { params: { query: range } }),
      apiClient.GET("/analytics/timeseries", {
        params: { query: { metric: "published_posts", granularity: "week" } },
      }),
      apiClient.GET("/analytics/attribution", { params: { query: range } }),
      apiClient.GET("/calendar", {
        params: { query: range },
      }),
      apiClient.GET("/analytics/failed-posts", { params: { query: range } }),
    ]);

    if (
      summary.error ||
      !summary.data ||
      timeseries.error ||
      !timeseries.data ||
      attribution.error ||
      !attribution.data ||
      failedPostsReq.error ||
      !failedPostsReq.data
    ) {
      return { ok: false, message: "Chưa tải được báo cáo, thử lại giúp bạn nhé." };
    }

    const topPosts: TopPostItem[] = [];
    if (calendarData.data?.days) {
      for (const day of calendarData.data.days) {
        for (const item of day.items) {
          if (item.status === "published") {
            topPosts.push({
              id: item.id,
              channel: item.channel,
              caption: item.text || (item as unknown as { caption?: string }).caption || "",
              published_at: item.scheduled_at,
            });
          }
        }
      }
    }

    return {
      ok: true,
      data: {
        summary: summary.data,
        timeseries: timeseries.data,
        attribution: attribution.data,
        topPosts,
        failedPosts: failedPostsReq.data,
      },
    };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
