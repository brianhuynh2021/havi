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

export type DashboardContentSummary = components["schemas"]["DashboardContentSummary"] & {
  broken_connections: number;
  unhandled_inbox: number;
  total_connections: number;
};
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
    return { ok: true, data: data as DashboardContentSummary };
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
