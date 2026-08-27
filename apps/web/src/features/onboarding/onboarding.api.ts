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
// Dùng `translateNow` thay hook: module này không phải component nên không gọi
// `useLanguage()` được. Đặt bí danh `t` để chỉ có MỘT tên phải nhớ, và để
// `scripts/i18n-audit.mjs` đếm được như mọi chỗ gọi khác.
import { translateNow as t } from "@/lib/i18n/language-context";
import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, toStoredTokens } from "@/features/auth/auth.api";
import { readTokens, type StoredTokens } from "@/lib/auth/token-store";

/** Tên đã nhập lúc đăng ký, để điền sẵn ô "Tên tiệm".
 *
 * Chỉ là tiện nghi — hỏng thì trả chuỗi rỗng và user tự gõ, không chặn
 * onboarding và không hiện lỗi. */
export async function fetchDefaultShopName(): Promise<string> {
  try {
    const { data } = await apiClient.GET("/auth/me");
    return data?.name ?? "";
  } catch {
    return "";
  }
}

export type CreateWorkspaceResult =
  | { ok: true; tokens: StoredTokens }
  | { ok: false; message: string };

/**
 * Bước 1 onboarding: tạo tiệm hoặc cập nhật tiệm (Idempotent).
 *
 * Nếu đã có `existingWorkspaceId` (ví dụ user quay lại từ bước 2 để sửa tên),
 * gọi `PATCH /workspaces/{id}` để cập nhật thay vì tạo tiệm thứ 2 trùng tên.
 */
export async function saveWorkspace(
  name: string,
  existingWorkspaceId?: string | null,
): Promise<CreateWorkspaceResult> {
  try {
    if (existingWorkspaceId) {
      const updated = await apiClient.PATCH("/workspaces/{workspace_id}", {
        params: { path: { workspace_id: existingWorkspaceId } },
      // `industry` đã là tuỳ chọn ở backend (mặc định `other`) sau khi bước chọn
      // ngành bị gỡ khỏi onboarding. Vẫn truyền thẳng ở đây vì
      // `openapi-typescript` coi field có `default` là bắt buộc trong request
      // body — sửa chỗ đó là đổi cấu hình sinh type cho cả dự án, đắt hơn một
      // dòng này.
        body: { name, industry: "other" },
      });
      if (updated.error || !updated.data) {
        return {
          ok: false,
          message: "Chưa cập nhật được thông tin tiệm, thử lại giúp bạn nhé.",
        };
      }
      const tokens = readTokens();
      if (!tokens) {
        return { ok: false, message: "Phiên đăng nhập không hợp lệ" };
      }
      return { ok: true, tokens };
    }

    const created = await apiClient.POST("/workspaces", {
    // `industry` đã là tuỳ chọn ở backend (mặc định `other`) sau khi bước chọn
    // ngành bị gỡ khỏi onboarding. Vẫn truyền thẳng ở đây vì
    // `openapi-typescript` coi field có `default` là bắt buộc trong request
    // body — sửa chỗ đó là đổi cấu hình sinh type cho cả dự án, đắt hơn một
    // dòng này.
      body: { name, industry: "other" },
    });
    if (created.error || !created.data) {
      return {
        ok: false,
        message: "Chưa tạo được tiệm, thử lại giúp bạn nhé.",
      };
    }

    const activated = await apiClient.POST(
      "/workspaces/{workspace_id}/activate",
      { params: { path: { workspace_id: created.data.id } } },
    );
    if (activated.error || !activated.data) {
      return {
        ok: false,
        message: "Đã tạo tiệm nhưng chưa vào được, thử lại giúp bạn nhé.",
      };
    }

    return { ok: true, tokens: toStoredTokens(activated.data) };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export const createWorkspace = saveWorkspace;

/**
 * Khởi tạo brand profile cho workspace mới.
 *
 * Không còn nhận ngành nghề. Onboarding từng có một bước chọn ngành để đoán giọng
 * văn, nhưng ngành chỉ được copy sang brand profile rồi không ai đọc — và sản
 * phẩm là một hàng đợi việc, thứ mà ngành nghề không ảnh hưởng gì tới.
 *
 * Giọng mặc định để trung tính có chủ ý: một giọng Havi đoán sẵn theo ngành đọc
 * như thật nhưng không phải giọng của cơ sở nào cả. Chủ đặt lại ở Cài đặt, nơi
 * họ thấy được mình đang đổi cái gì.
 */
export async function initializeBusinessTruthPack(
  shopName: string,
): Promise<{ ok: boolean; message?: string }> {
  try {
    const tone = t("Chuyên nghiệp, thân thiện, tận tâm phục vụ khách hàng tại {shopName}.", { shopName: shopName });

    // **Không seed FAQ nào cả.**
    //
    // Bản trước nạp sẵn một bộ FAQ đoán theo ngành: giờ mở cửa, lớp học thử, cam
    // kết đầu ra — toàn bộ là số bịa, kèm chú thích rằng chủ tiệm sẽ sửa lại cho
    // đúng. Chúng vào với `approved: false` nên Havi chưa tự gửi, nhưng đó là
    // một hàng rào mỏng: người dùng mở Cài đặt, thấy một danh sách trông đã hoàn
    // chỉnh, và bấm duyệt cả loạt mà không đọc từng câu.
    //
    // FAQ có thể trở thành gợi ý trả lời, nên đoán sai vẫn làm người dùng mất
    // công kiểm tra và dễ gửi nhầm. Thứ Havi không biết thì Havi không viết ra:
    // FAQ để rỗng, người dùng nhập câu thật ở Cài đặt.
    const faq: Array<{ question: string; answer: string; approved: boolean }> = [];

    await apiClient.PUT("/brand-profile", {
      body: {
        tone,
        faq,
      },
    });

    // Onboarding KHÔNG đặt mục tiêu hộ người dùng.
    //
    // Bản trước âm thầm tạo một Goal ("Thu hút 20 khách hàng… trong 30 ngày")
    // kèm một Roadmap, chỉ dựa trên ngành nghề vừa chọn. Người dùng chưa từng
    // nói họ muốn 20 khách, chưa từng nói 30 ngày, và không hề biết Havi vừa
    // cam kết điều đó thay mình.
    //
    // Havi quản trị hệ thống social của khách, không quản trị mục tiêu kinh
    // doanh của khách. Toàn bộ tầng Goal/Roadmap/Evidence đã được gỡ khỏi sản
    // phẩm ngày 2026-08-25.

    return { ok: true };
  } catch {
    // Non-blocking fallback
    return { ok: true };
  }
}

