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

export type InboxItem = components["schemas"]["InboxItem"];
export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const GENERIC_ERROR = "Có lỗi xảy ra, thử lại giúp bạn nhé.";

export async function listInbox(): Promise<Result<InboxItem[]>> {
  try {
    const { data, error } = await apiClient.GET("/inbox");
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data: data.items ?? [] };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function sendInboxReply(id: string, text: string): Promise<Result<InboxItem>> {
  try {
    const { data, error } = await apiClient.POST("/inbox/{item_id}/reply", {
      params: { path: { item_id: id } },
      body: { text },
    });
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function dismissInboxItem(id: string): Promise<Result<void>> {
  try {
    const { error } = await apiClient.POST("/inbox/{item_id}/dismiss", {
      params: { path: { item_id: id } },
    });
    if (error) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data: undefined };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
