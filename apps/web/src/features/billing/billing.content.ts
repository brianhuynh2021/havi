// i18n-data: mọi chuỗi ở đây là **dữ liệu**, được `t()` dịch ở chỗ render trong
// `billing-screen.tsx`. Tách ra file riêng để `scripts/i18n-audit.mjs` phân biệt
// được "dữ liệu dịch chỗ khác" với "chuỗi bị bỏ quên" — nếu để chung một file
// thì phải miễn cả file, và lúc đó những chuỗi thật sự bị bỏ quên cũng lọt.
//
// Cùng cách tổ chức với `features/landing/landing.content.ts`.
/**
 * Nội dung bảng giá và nhãn trạng thái đăng ký.
 *
 * Giá để dạng chuỗi chứ không phải số vì chúng là **chuỗi cần dịch**: tiếng Việt
 * viết `189.000 đ`, tiếng Anh viết `189,000 ₫`. Dấu phân cách nghìn và vị trí ký
 * hiệu tiền là chuyện của từng ngôn ngữ, không phải của phép định dạng số.
 */

import type { Plan } from "./billing.api";

export const PLAN_DETAILS: Record<
  Plan,
  {
    title: string;
    price: string;
    annualPrice: string;
    period: string;
    dailyNote: string;
    badge: string | null;
    badgeTone: "popular" | "featured" | "enterprise" | null;
    desc: string;
    features: string[];
  }
> = {
  trial: {
    title: "Gói trải nghiệm",
    price: "0 đ",
    annualPrice: "0 đ",
    period: "/ 7 ngày",
    dailyNote: "Miễn phí 100% · Không cần thẻ",
    badge: null,
    badgeTone: null,
    desc: "Chạy thử vòng vận hành: nối kênh, soạn, duyệt, đăng và trả lời.",
    features: [
      "7 ngày dùng đầy đủ, không cần thẻ",
      "2 người dùng · Facebook Page + Reels + Messenger",
      "Hộp thư Messenger gộp về một nơi",
      "Quy trình soạn → duyệt → đăng có ràng buộc",
      "Hạn mức AI dùng thử khoảng 30 bài",
    ],
  },
  tiem_nho: {
    title: "Gói khởi nghiệp",
    price: "189.000 đ",
    annualPrice: "1.890.000 đ",
    period: "/ tháng",
    dailyNote: "Chỉ ~6.000 đ/ngày",
    badge: null,
    badgeTone: null,
    desc: "Một thương hiệu, một đội nhỏ, mọi việc social trong tầm kiểm soát.",
    features: [
      "3 người dùng · Facebook Page + Reels + Messenger",
      "Lịch đăng, thư viện media và kho nội dung dùng chung",
      "Hộp thư Messenger kèm trạng thái đã xử lý hay chưa",
      "Lịch sử hoạt động: ai làm gì, lúc nào, kết quả ra sao",
      "Hạn mức AI soạn nháp khoảng 130 bài mỗi tháng",
    ],
  },
  toan_dien: {
    title: "Gói chuyên nghiệp",
    price: "369.000 đ",
    annualPrice: "3.690.000 đ",
    period: "/ tháng",
    dailyNote: "Chỉ ~12.000 đ/ngày",
    badge: "🌟 Khuyên dùng",
    badgeTone: "popular",
    desc: "Dành cho đội nhiều người: ai được soạn, ai được duyệt, ai trực hội thoại.",
    features: [
      "10 người dùng · Facebook Page + Reels + Messenger",
      "Phân quyền theo vai: chủ, người soạn, người duyệt",
      "Người soạn không đăng được — quyền được kiểm ở máy chủ",
      "Đăng Facebook Page và Reels sau khi có người phê duyệt",
      "Báo cáo xuất bản và hội thoại theo dữ liệu nền tảng",
      "Hạn mức AI soạn nháp cao, hỗ trợ kỹ thuật trực tiếp",
    ],
  },
  doanh_nghiep: {
    title: "Chuỗi doanh nghiệp",
    price: "799.000 đ",
    annualPrice: "7.990.000 đ",
    period: "/ tháng",
    dailyNote: "Chỉ ~26.000 đ/ngày",
    badge: null,
    badgeTone: null,
    desc: "Nhiều thương hiệu hoặc chi nhánh dưới một tầng quản trị. Mỗi thương hiệu tính gói riêng.",
    features: [
      "50 người dùng · Facebook Page + Reels + Messenger đa thương hiệu",
      "Tầng doanh nghiệp: gom nhiều thương hiệu, nhìn chéo sức khoẻ mọi kênh",
      "Giọng thương hiệu và danh sách điều không được hứa, theo từng đơn vị",
      "Hỗ trợ triển khai trực tiếp cùng Founder và đội ngũ",
      "Hạn mức AI cao nhất · xuất hoá đơn VAT điện tử",
    ],
  },
};

/**
 * Nhãn tiếng Việt cho `SubscriptionStatus`.
 *
 * Bản trước viết `sub.status === "active" ? "Đang hoạt động" : sub.status` — nên
 * mọi trạng thái khác `active` lọt nguyên giá trị enum tiếng Anh ra màn hình:
 * workspace đang dùng thử thấy chữ **"trialing"**, hết hạn thấy **"past_due"**.
 * Đó là loại lỗi chỉ hiện ở đúng những lúc người dùng cần đọc hiểu nhất.
 */
export const STATUS_LABELS: Record<string, string> = {
  trialing: "Đang dùng thử",
  active: "Đang hoạt động",
  past_due: "Đã hết hạn",
  canceled: "Đã huỷ",
};
