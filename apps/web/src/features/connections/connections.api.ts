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
import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE } from "@/features/auth/auth.api";
import type { components } from "@/lib/api-client/schema";

export type PlatformConnection = components["schemas"]["PlatformConnection"];
export type Platform = components["schemas"]["Platform"];
export type ConnectionStatus = components["schemas"]["ConnectionStatus"];

/** Nơi backend đưa người dùng về sau khi cấp quyền xong. Nối kênh từ Cài đặt
 * phải quay về Cài đặt, không bị đá vào wizard onboarding. */
export type OAuthReturnTarget = components["schemas"]["OAuthReturnTarget"];

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const GENERIC_ERROR = "Có lỗi xảy ra, thử lại giúp bạn nhé.";

/** Kênh chưa có adapter thật thì backend trả 501 — UI phải nói "chưa hỗ trợ",
 * không được hiện "đã nối" cho một kênh chỉ có trên giấy (ROADMAP Tuần 7). */
const NOT_SUPPORTED = "Havi chưa nối được kênh này — sắp có ạ.";
const NOT_CONFIGURED =
  "Kênh này chưa được cấu hình trên hệ thống — bạn báo Havi giúp nhé.";

export async function listConnections(): Promise<Result<PlatformConnection[]>> {
  try {
    const { data, error } = await apiClient.GET("/connections");
    if (error || !data) return { ok: false, message: GENERIC_ERROR };
    // Kiểm là mảng thật chứ không tin kiểu của generated client: kiểu đó mô tả
    // hợp đồng, không phải thứ đã về trên dây. Một proxy trả HTML lỗi hay một
    // API version lệch sẽ làm `.map` ném và đổ cả sidebar — trong khi thứ này
    // chỉ là chip trang trí.
    if (!Array.isArray(data)) return { ok: false, message: GENERIC_ERROR };
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/**
 * Bắt đầu nối kênh: xin URL cấp quyền rồi *điều hướng cả trang* sang nền tảng.
 *
 * Không mở popup và không `fetch` cái URL đó: màn hình cấp quyền của Facebook
 * phải hiện trên thanh địa chỉ thật để chủ tiệm thấy được domain facebook.com —
 * đó là cách duy nhất họ kiểm được mình không đang gõ mật khẩu vào trang giả.
 * Popup còn bị chặn mặc định trên nhiều máy.
 *
 * Hàm này không trả về khi thành công (trang đã chuyển đi). Backend redirect
 * ngược lại `/onboarding?ket_noi=ok|loi` sau khi xong.
 */
export async function startConnect(
  platform: Platform,
  returnTo: OAuthReturnTarget,
  options: { openPopup?: boolean } = { openPopup: true },
): Promise<Result<{ popupOpened: boolean }>> {
  try {
    const { data, error, response } = await apiClient.POST(
      "/connections/{platform}/start",
      { params: { path: { platform }, query: { tro_ve: returnTo } } },
    );
    if (error || !data) {
      if (response?.status === 501) return { ok: false, message: NOT_SUPPORTED };
      if (response?.status === 503) return { ok: false, message: NOT_CONFIGURED };
      return { ok: false, message: "Chưa mở được trang cấp quyền, thử lại nhé." };
    }

    if (options.openPopup && typeof window !== "undefined") {
      try {
        const width = 620;
        const height = 750;
        const left = window.screenX + Math.max(0, (window.outerWidth - width) / 2);
        const top = window.screenY + Math.max(0, (window.outerHeight - height) / 2);
        const popup = window.open(
          data.authorization_url,
          `havi_oauth_${platform}`,
          `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,status=yes`,
        );
        if (popup) {
          popup.focus();
          return { ok: true, data: { popupOpened: true } };
        }
      } catch {
        // Môi trường test jsdom hoặc trình duyệt chặn popup — fallback điều hướng thường
      }
    }

    window.location.assign(data.authorization_url);
    return { ok: true, data: { popupOpened: false } };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function disconnect(platform: Platform): Promise<Result<null>> {
  try {
    const { error, response } = await apiClient.DELETE("/connections/{platform}", {
      params: { path: { platform } },
    });
    // 204 không có body nên `data` luôn undefined — chỉ được nhìn `error`.
    if (error) {
      return {
        ok: false,
        message:
          response?.status === 404
            ? "Kênh này chưa được nối."
            : "Chưa ngắt được kênh, thử lại giúp bạn nhé.",
      };
    }
    return { ok: true, data: null };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

/** Lý do lỗi mà backend gắn vào URL redirect sau callback OAuth.
 *
 * Backend cố ý KHÔNG đưa `error_description` thô của nền tảng vào URL (chuỗi do
 * bên thứ ba kiểm soát), nên phía này dịch từ mã ngắn sang câu tiếng Việt. */
const CALLBACK_ERRORS: Record<string, string> = {
  huy: "Bạn đã bấm Huỷ ở Facebook nên kênh chưa được nối.",
  thieu_thong_tin: "Facebook trả về thiếu thông tin — bạn thử nối lại nhé.",
  het_han: "Lượt nối kênh đã hết hạn (quá 10 phút) — bạn bấm nối lại nhé.",
  chua_cau_hinh: NOT_CONFIGURED,
  tam_loi: "Nền tảng đang bận — bạn bấm nối lại sau ít phút nhé.",
  he_thong: "Havi gặp lỗi khi nối kênh — bạn thử lại sau chút nhé.",
};

export type CallbackOutcome =
  | { kind: "ok" }
  | { kind: "error"; message: string }
  | null;

/** Đọc `?ket_noi=ok|loi&ly_do=...` mà backend gắn vào URL redirect. */
export function readCallbackOutcome(search: string): CallbackOutcome {
  const params = new URLSearchParams(search);
  const ketNoi = params.get("ket_noi");
  if (ketNoi === "ok") return { kind: "ok" };
  if (ketNoi !== "loi") return null;
  const lyDo = params.get("ly_do") ?? "";
  // `tu_choi` mang theo câu giải thích của chính nền tảng (đã được backend cắt
  // ngắn và encode). Hiện nguyên câu đó thay vì "lỗi hệ thống" chung chung:
  // nó nói rõ thiếu quyền nào hoặc chưa có Trang nào, tức là việc cần làm tiếp.
  if (lyDo === "tu_choi") {
    const chiTiet = params.get("chi_tiet")?.trim();
    if (chiTiet) return { kind: "error", message: chiTiet };
  }
  return { kind: "error", message: CALLBACK_ERRORS[lyDo] ?? GENERIC_ERROR };
}

export const PILOT_PLATFORMS: { platform: Platform; label: string }[] = [
  { platform: "facebook", label: "Facebook Fanpage, Reels & Messenger" },
];

export function isUsable(connection: PlatformConnection | undefined): boolean {
  return connection?.status === "connected";
}

/** Câu giải thích + hành động cho từng trạng thái kết nối.
 *
 * `expired` và `revoked` đều dẫn tới cùng một việc (nối lại), nhưng nói lý do
 * khác nhau: token hết hạn là chuyện bình thường theo thời gian, còn mất quyền
 * thường là do ai đó đổi vai trò trên Page — chủ tiệm cần biết để kiểm lại. */
export function statusCopy(status: ConnectionStatus): {
  label: string;
  hint: string;
  needsReconnect: boolean;
} {
  switch (status) {
    case "connected":
      return { label: "Đã nối", hint: "", needsReconnect: false };
    case "expired":
      return {
        label: "Hết hạn",
        hint: "Facebook đã hết hạn cấp quyền — bạn nối lại để Havi đăng bài tiếp nhé.",
        needsReconnect: true,
      };
    case "revoked":
      return {
        label: "Mất quyền",
        hint: "Havi không còn quyền đăng trên Page này — bạn kiểm lại quyền quản trị rồi nối lại nhé.",
        needsReconnect: true,
      };
  }
}


/** Tính năng một kết nối có thể thiếu, kèm câu nói rõ mất gì.
 *
 * Kênh giờ nối được với ít quyền hơn toàn bộ (backend:
 * `domain/policies/connection_capabilities.py`), nên thẻ kết nối phải nói ra
 * cái gì đang tắt. Im lặng ở đây đưa ta về đúng vấn đề cũ — chấm xanh trong khi
 * Inbox không nhận gì — chỉ khác là lần này Havi biết mà không nói. */
const CAPABILITY_LABELS: Record<string, string> = {
  publish_post: "Đăng bài",
  reply_comment: "Trả lời bình luận",
  reply_message: "Trả lời tin nhắn",
  receive_inbox: "Nhận tin về Hộp thư",
};

/** Tính năng kênh này KHÔNG dùng được, theo thứ tự ổn định để UI không nhảy. */
export function missingCapabilities(
  connection: PlatformConnection | undefined,
): string[] {
  if (!connection) return [];
  const granted = new Set(connection.capabilities ?? []);
  // `capabilities` rỗng cũng có thể là kết nối cũ backend chưa ghi quyền. Backend
  // đã quy ước trả đủ khả năng cho trường hợp đó, nên rỗng ở đây là rỗng thật.
  return Object.entries(CAPABILITY_LABELS)
    .filter(([key]) => !granted.has(key))
    .map(([, label]) => label);
}
