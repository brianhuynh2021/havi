import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, toStoredTokens } from "@/features/auth/auth.api";
import type { StoredTokens } from "@/lib/auth/token-store";
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
 * Bước 1 onboarding: tạo tiệm rồi lấy token mới.
 *
 * Hai lượt gọi chứ không một: `POST /workspaces` tạo tiệm và set nó thành
 * active ở phía DB, nhưng JWT đang cầm trên tay được ký từ trước đó nên vẫn
 * mang `needs_onboarding: true` và không có `active_workspace_id`. Chỉ
 * `/workspaces/{id}/activate` mới ký lại token. Bỏ bước này thì user tạo tiệm
 * xong vẫn bị route guard đá ngược về /onboarding — vòng lặp không lối ra.
 */
export async function createWorkspace(
  name: string,
  industry: IndustryOption["value"],
): Promise<CreateWorkspaceResult> {
  try {
    const created = await apiClient.POST("/workspaces", {
      body: { name, industry },
    });
    if (created.error || !created.data) {
      return {
        ok: false,
        message: "Chưa tạo được tiệm, thử lại giúp chị nhé.",
      };
    }

    const activated = await apiClient.POST(
      "/workspaces/{workspace_id}/activate",
      { params: { path: { workspace_id: created.data.id } } },
    );
    if (activated.error || !activated.data) {
      // Tiệm đã tạo thật, chỉ token là cũ. Nói theo hướng "thử lại" thay vì
      // "tạo lại" để chủ tiệm không bấm tạo thêm tiệm thứ hai trùng tên.
      return {
        ok: false,
        message: "Đã tạo tiệm nhưng chưa vào được, thử lại giúp chị nhé.",
      };
    }

    return { ok: true, tokens: toStoredTokens(activated.data) };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

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

    const faqMap: Record<string, Array<{ question: string; answer: string; approved: boolean }>> = {
      spa: [
        {
          question: "Tiệm có làm việc cuối tuần không?",
          answer: `${shopName} mở cửa phục vụ xuyên suốt từ 8h30 đến 20h30 tất cả các ngày trong tuần kể cả Thứ 7 & Chủ Nhật ạ.`,
          approved: true,
        },
        {
          question: "Có cần đặt lịch trước không?",
          answer: `Dạ để được phục vụ chu đáo nhất và không phải chờ đợi, chị/anh vui lòng nhắn trước cho ${shopName} thời gian dự kiến nhé ạ!`,
          approved: true,
        },
      ],
      restaurant: [
        {
          question: "Quán mở cửa mấy giờ?",
          answer: `${shopName} mở cửa từ 7h00 đến 22h30 hàng ngày ạ.`,
          approved: true,
        },
        {
          question: "Có nhận đặt bàn trước không?",
          answer: `Dạ ${shopName} có nhận đặt bàn trước cho tiệc gia đình, bạn bè ạ. Chị/anh báo số lượng khách và giờ đến nhé!`,
          approved: true,
        },
      ],
      clinic: [
        {
          question: "Phòng khám có đặt lịch khám trước không?",
          answer: `Dạ có ạ, quý khách vui lòng đặt hẹn trước với ${shopName} để được bác sĩ tư vấn chu đáo nhất.`,
          approved: true,
        },
      ],
      other: [
        {
          question: "Tiệm mở cửa khung giờ nào?",
          answer: `${shopName} mở cửa từ 8h00 đến 21h00 hàng ngày ạ.`,
          approved: true,
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

    return { ok: true };
  } catch {
    // Non-blocking fallback
    return { ok: true };
  }
}

