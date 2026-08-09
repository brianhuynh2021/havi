import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import { apiClient } from "@/lib/api-client/client";
import type { components } from "@/lib/api-client/schema";

export type DashboardContentSummary =
  components["schemas"]["DashboardContentSummary"];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

export async function fetchDashboardSummary(): Promise<
  Result<DashboardContentSummary>
> {
  try {
    const { data, error } = await apiClient.GET("/analytics/dashboard");
    if (error || !data) {
      return { ok: false, message: "Chưa tải được tổng quan, thử lại giúp chị nhé." };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
