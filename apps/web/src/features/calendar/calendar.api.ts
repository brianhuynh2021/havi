import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import type { ContentItem, Result } from "@/features/content-creation/content-creation.api";
import type { components } from "@/lib/api-client/schema";

export type CalendarDay = components["schemas"]["CalendarDay"];

const GENERIC_ERROR = "Chưa tải được lịch, thử lại giúp bạn nhé.";

/** Ngày `YYYY-MM-DD` theo giờ Việt Nam.
 *
 * Không dùng `toISOString()`: nó đổi sang UTC trước, nên 6h sáng thứ Ba ở VN
 * thành 23h thứ Hai UTC và cả tuần lệch một ngày. Backend cũng gom nhóm theo
 * ngày VN nên hai bên phải nói cùng một thứ ngày. */
export function toVnDateString(date: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

/** Thứ Hai của tuần chứa `date`, tính theo giờ VN. Tuần Việt Nam bắt đầu từ
 * thứ Hai, khác mặc định Chủ Nhật của `getDay()`. */
export function startOfVnWeek(date: Date): Date {
  const vnDay = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    weekday: "short",
  }).format(date);
  const order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const offset = Math.max(0, order.indexOf(vnDay));
  const monday = new Date(date);
  monday.setDate(monday.getDate() - offset);
  return monday;
}

export function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

/** 
 * Ngày thứ Hai của tuần chứa ngày mùng 1 của tháng hiện tại.
 * Dùng để vẽ lưới lịch 42 ô (6 tuần). 
 */
export function startOfVnMonthGrid(date: Date): Date {
  const firstDayOfMonth = new Date(date.getFullYear(), date.getMonth(), 1);
  return startOfVnWeek(firstDayOfMonth);
}

export async function fetchCalendar(
  start: string,
  end: string,
): Promise<Result<CalendarDay[]>> {
  try {
    const { data, error } = await apiClient.GET("/calendar", {
      params: { query: { start, end } },
    });
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data: data.days };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/** Đổi giờ đăng. `scheduledAt` phải là ISO có offset — gửi chuỗi naive thì
 * backend hiểu thành UTC và bài nhảy 7 tiếng. */
export async function rescheduleItem(
  itemId: string,
  scheduledAt: string,
): Promise<Result<ContentItem>> {
  try {
    const { data, error, response } = await apiClient.POST(
      "/calendar/{content_id}/reschedule",
      {
        params: { path: { content_id: itemId } },
        body: { scheduled_at: scheduledAt },
      },
    );
    if (error || !data) {
      return {
        ok: false,
        message:
          response?.status === 409
            ? "Bài đã đăng rồi nên không đổi lịch được nữa."
            : "Chưa đổi được lịch, thử lại giúp bạn nhé.",
      };
    }
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}
