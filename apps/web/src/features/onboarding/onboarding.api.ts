import { apiClient } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, toStoredTokens } from "@/features/auth/auth.api";
import { createGoal, generateRoadmap } from "@/features/roadmap/roadmap.api";
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
        message: "Chưa tạo được tiệm, thử lại giúp bạn nhé.",
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
        message: "Đã tạo tiệm nhưng chưa vào được, thử lại giúp bạn nhé.",
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
      education: [
        {
          question: "Trung tâm có lớp học thử miễn phí không?",
          answer: `Dạ ${shopName} có chương trình Học thử 1 buổi miễn phí trải nghiệm thực hành thực tế ạ! Anh/chị cho em xin Tên & SĐT để thầy giáo xếp lịch cho mình/bé nhé!`,
          approved: true,
        },
        {
          question: "Khóa học đào tạo trong bao lâu và có cam kết đầu ra không?",
          answer: `Dạ khóa học tại ${shopName} kéo dài từ 2-3 tháng, đào tạo 1 kèm 1 thực hành trên dự án thật và cam kết hỗ trợ học viên đến khi làm được sản phẩm chạy thực tế ạ!`,
          approved: true,
        },
        {
          question: "Thời gian học như thế nào, có lớp buổi tối hay cuối tuần không?",
          answer: `Dạ ${shopName} có đầy đủ các ca học linh hoạt: Sáng (8h30-10h30), Chiều (14h-16h), Tối (18h30-20h30) và ca Thứ 7 & Chủ Nhật để học viên dễ dàng sắp xếp ạ.`,
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

    // Tự động khởi tạo Mục Tiêu & Lộ Trình mẫu để khi bước vào app có ngay việc làm
    try {
      const goalTitles: Record<string, { title: string; evidence: string }> = {
        spa: {
          title: `Thu hút 20 khách hàng trải nghiệm dịch vụ mới tại ${shopName} trong 30 ngày`,
          evidence: "Có 20 khách hàng để lại số điện thoại hoặc đặt lịch trải nghiệm",
        },
        restaurant: {
          title: `Tăng 30% khách hàng ghé quán & đặt bàn tại ${shopName}`,
          evidence: "Ghi nhận 30 lượt khách đặt bàn hoặc check-in tại quán",
        },
        retail: {
          title: `Thu hút 20 khách hàng mua sắm & để lại thông tin tại ${shopName}`,
          evidence: "Có 20 đơn hàng mới hoặc khách hàng mới để lại thông tin",
        },
        clinic: {
          title: `Thu hút 15 bệnh nhân đặt hẹn khám tư vấn tại ${shopName}`,
          evidence: "Có 15 lượt bệnh nhân đặt lịch khám tư vấn",
        },
        education: {
          title: `Tuyển sinh 20 học viên khóa học mới tại ${shopName} trong 30 ngày`,
          evidence: "Có 20 học viên đăng ký hoặc chuyển khoản cọc VietQR",
        },
        other: {
          title: `Thu hút 20 khách hàng tiềm năng đầu tiên tại ${shopName} trong 30 ngày`,
          evidence: "Có 20 khách hàng liên hệ tư vấn hoặc để lại số điện thoại",
        },
      };

      const selectedGoal = industry ? (goalTitles[industry] ?? goalTitles.other) : goalTitles.other;
      const goalRes = await createGoal({
        title: selectedGoal.title,
        category: "acquire_customers",
        evidence_definition: selectedGoal.evidence,
        weekly_capacity_hours: 10,
      });

      if (goalRes.ok) {
        await generateRoadmap(goalRes.data.id);
      }
    } catch {
      // Non-blocking fallback
    }

    return { ok: true };
  } catch {
    // Non-blocking fallback
    return { ok: true };
  }
}


