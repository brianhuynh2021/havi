import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import { apiClient } from "@/lib/api-client/client";
import type { components } from "@/lib/api-client/schema";

export type OperationsMetrics = components["schemas"]["OperationsMetrics"];
export type OperationsProviderMetric =
  components["schemas"]["OperationsProviderMetric"];

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

export function operationsWindow(now = new Date()): { start: string; end: string } {
  const end = toVnDate(now);
  const startDate = new Date(now);
  startDate.setDate(startDate.getDate() - 6);
  return { start: toVnDate(startDate), end };
}

export async function fetchOperationsMetrics(): Promise<Result<OperationsMetrics>> {
  try {
    const { data, error } = await apiClient.GET("/analytics/operations", {
      params: { query: operationsWindow() },
    });
    if (error || !data) {
      return { ok: false, message: "Chưa tải được số liệu vận hành." };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
