import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import { apiClient } from "@/lib/api-client/client";
import type { components } from "@/lib/api-client/schema";

export type DashboardContentSummary =
  components["schemas"]["DashboardContentSummary"];
export type DashboardActivityEvent = components["schemas"]["EventLogRecord"];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

export async function fetchDashboardSummary(): Promise<
  Result<DashboardContentSummary>
> {
  try {
    const { data, error } = await apiClient.GET("/analytics/dashboard");
    if (error || !data) {
      return { ok: false, message: "Chưa tải được tổng quan, thử lại giúp bạn nhé." };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function fetchDashboardActivity(): Promise<
  Result<DashboardActivityEvent[]>
> {
  try {
    const { data, error } = await apiClient.GET("/analytics/events", {
      params: { query: { limit: 5 } },
    });
    if (error || !data) {
      return { ok: false, message: "Chưa tải được hoạt động gần đây." };
    }
    return { ok: true, data: data.items };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
