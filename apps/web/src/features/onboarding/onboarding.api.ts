import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, toStoredTokens } from "@/features/auth/auth.api";
import { readTokens, type StoredTokens } from "@/lib/auth/token-store";
import type { IndustryOption } from "./onboarding.fixture";

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
  industry: IndustryOption["value"],
  existingWorkspaceId?: string | null,
): Promise<CreateWorkspaceResult> {
  try {
    if (existingWorkspaceId) {
      const updated = await apiClient.PATCH("/workspaces/{workspace_id}", {
        params: { path: { workspace_id: existingWorkspaceId } },
        body: { name, industry },
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
      body: { name, industry },
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

export async function initializeBusinessTruthPack(
  industry: IndustryOption["value"] | null,
  shopName: string,
): Promise<{ ok: boolean; message?: string }> {
  try {
    const toneMap: Record<string, string> = {
      spa: `Chuyên nghiệp, dịu dàng, chu đáo chuẩn spa làm đẹp ${shopName}. Luôn ân cần chăm sóc khách hàng.`,
      restaurant: `Hào hứng, hấp dẫn, ấm cúng chuẩn ẩm thực & đồ uống ${shopName}.`,
      retail: `Nhiệt tình, rõ ràng, tập trung chất lượng sản phẩm và ưu đãi tại ${shopName}.`,
      clinic: `Chuẩn y khoa, tin cậy, nhẹ nhàng và thấu hiểu bệnh nhân tại ${shopName}.`,
      education: `Truyền cảm hứng, bài bản, thực chiến và tận tâm tại ${shopName}.`,
      other: `Chuyên nghiệp, thân thiện, tận tâm phục vụ khách hàng tại ${shopName}.`,
    };

    const tone = industry ? (toneMap[industry] ?? toneMap.other) : toneMap.other;

    // FAQ mẫu theo ngành — **luôn `approved: false`**.
    //
    // Đây là câu chữ Havi *đoán* cho một ngành, không phải sự thật về cơ sở
    // này: giờ mở cửa, lớp học thử, cam kết đầu ra đều là số bịa để chủ tiệm
    // sửa lại cho đúng. Trước đây chúng vào thẳng với `approved: true`, nghĩa
    // là Havi có thể tự nhắn cho khách thật một giờ mở cửa mà chủ tiệm chưa
    // từng nhìn thấy.
    //
    // Câu trả lời tự động là đường duy nhất trong Havi đi tới người ngoài mà
    // không qua mắt chủ tiệm. Nói sai với khách thì không rút lại được.
    const faqMap: Record<string, Array<{ question: string; answer: string; approved: boolean }>> = {
      spa: [
        {
          question: "Tiệm có làm việc cuối tuần không?",
          answer: `${shopName} mở cửa phục vụ xuyên suốt từ 8h30 đến 20h30 tất cả các ngày trong tuần kể cả Thứ 7 & Chủ Nhật ạ.`,
          approved: false,
        },
        {
          question: "Có cần đặt lịch trước không?",
          answer: `Dạ để được phục vụ chu đáo nhất và không phải chờ đợi, chị/anh vui lòng nhắn trước cho ${shopName} thời gian dự kiến nhé ạ!`,
          approved: false,
        },
      ],
      restaurant: [
        {
          question: "Quán mở cửa mấy giờ?",
          answer: `${shopName} mở cửa từ 7h00 đến 22h30 hàng ngày ạ.`,
          approved: false,
        },
        {
          question: "Có nhận đặt bàn trước không?",
          answer: `Dạ ${shopName} có nhận đặt bàn trước cho tiệc gia đình, bạn bè ạ. Chị/anh báo số lượng khách và giờ đến nhé!`,
          approved: false,
        },
      ],
      clinic: [
        {
          question: "Phòng khám có đặt lịch khám trước không?",
          answer: `Dạ có ạ, quý khách vui lòng đặt hẹn trước với ${shopName} để được bác sĩ tư vấn chu đáo nhất.`,
          approved: false,
        },
      ],
      education: [
        {
          question: "Trung tâm có lớp học thử miễn phí không?",
          answer: `Dạ ${shopName} có chương trình Học thử 1 buổi miễn phí trải nghiệm thực hành thực tế ạ! Anh/chị cho em xin Tên & SĐT để thầy giáo xếp lịch cho mình/bé nhé!`,
          approved: false,
        },
        {
          question: "Khóa học đào tạo trong bao lâu và có cam kết đầu ra không?",
          answer: `Dạ khóa học tại ${shopName} kéo dài từ 2-3 tháng, đào tạo 1 kèm 1 thực hành trên dự án thật và cam kết hỗ trợ học viên đến khi làm được sản phẩm chạy thực tế ạ!`,
          approved: false,
        },
        {
          question: "Thời gian học như thế nào, có lớp buổi tối hay cuối tuần không?",
          answer: `Dạ ${shopName} có đầy đủ các ca học linh hoạt: Sáng (8h30-10h30), Chiều (14h-16h), Tối (18h30-20h30) và ca Thứ 7 & Chủ Nhật để học viên dễ dàng sắp xếp ạ.`,
          approved: false,
        },
      ],
      other: [
        {
          question: "Tiệm mở cửa khung giờ nào?",
          answer: `${shopName} mở cửa từ 8h00 đến 21h00 hàng ngày ạ.`,
          approved: false,
        },
      ],
    };

    const faq = industry ? (faqMap[industry] ?? faqMap.other) : faqMap.other;

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


