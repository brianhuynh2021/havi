export type IndustryOption = {
  value:
    | "spa"
    | "food_beverage"
    | "real_estate"
    | "professional"
    | "online_shop"
    | "other";
  label: string;
  icon: string;
  desc: string;
  recommended?: boolean;
};

// Khớp core.enums.Industry — Spa là ngành pilot đề xuất (ROADMAP.md §1 QA/product).
export const industryOptions: IndustryOption[] = [
  { value: "spa", label: "Spa / Tiệm làm đẹp", icon: "💆‍♀️", desc: "Viết bài liệu trình, nhắc lịch chăm sóc da", recommended: true },
  { value: "food_beverage", label: "Ăn uống & Cà phê", icon: "☕", desc: "Đăng món mới, ưu đãi kéo khách ghé quán" },
  { value: "real_estate", label: "Bất động sản", icon: "🏡", desc: "Bài đăng nhà đất & email báo giá chuẩn vị" },
  { value: "professional", label: "Dịch vụ chuyên môn", icon: "⚖️", desc: "Chia sẻ kinh nghiệm & khẳng định chuyên môn" },
  { value: "online_shop", label: "Bán hàng online", icon: "🛍️", desc: "Bài xả kho, chào hàng đa kênh & email chăm sóc" },
  { value: "other", label: "Ngành kinh doanh khác", icon: "✨", desc: "Thiết kế linh hoạt theo giọng văn tiệm của bạn" },
];
