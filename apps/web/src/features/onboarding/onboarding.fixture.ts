export type IndustryOption = {
  value:
    | "food_beverage"
    | "spa"
    | "retail_shop"
    | "online_shop"
    | "education"
    | "local_service"
    | "real_estate"
    | "professional"
    | "other";
  label: string;
  icon: string;
  desc: string;
  recommended?: boolean;
};

// Khớp core.enums.Industry — Hệ thống 8 ngành nghề toàn diện cho SMB & Doanh nghiệp
export const industryOptions: IndustryOption[] = [
  {
    value: "food_beverage",
    label: "Ăn uống, Cà phê & Tiệm bánh",
    icon: "☕",
    desc: "Đăng món mới và thực đơn mỗi ngày, hẹn giờ đăng vào khung đông người xem",
  },
  {
    value: "spa",
    label: "Spa, Thẩm mỹ & Làm đẹp",
    icon: "💆‍♀️",
    desc: "Viết bài liệu trình, feedback khách hàng, nhắc lịch chăm sóc & tư vấn giá",
    recommended: true,
  },
  {
    value: "retail_shop",
    label: "Cửa hàng bán lẻ & Shop thời trang",
    icon: "🛍️",
    desc: "Bài chào hàng, đăng clip giới thiệu sản phẩm, trả lời khách trong một hộp thư",
  },
  {
    value: "education",
    label: "Giáo dục, Ngoại ngữ & Đào tạo nghề",
    icon: "🎓",
    desc: "Tuyển sinh khóa mới, giới thiệu dự án học viên và chuẩn bị FAQ học phí đã duyệt",
  },
  {
    value: "local_service",
    label: "Chi nhánh dịch vụ, Y tế & Ngân hàng",
    icon: "🏦",
    desc: "Tăng nhận diện Google Maps địa phương, bài ưu đãi khai trương chi nhánh mới",
  },
  {
    value: "real_estate",
    label: "Bất động sản & Môi giới nhà đất",
    icon: "🏡",
    desc: "Từ ảnh bất động sản ra bài giới thiệu, đăng kèm clip bạn đã quay sẵn",
  },
  {
    value: "professional",
    label: "Dịch vụ chuyên môn & Tư vấn",
    icon: "⚖️",
    desc: "Chia sẻ kinh nghiệm chuyên môn, giữ nhịp đăng đều và không sót tin nhắn",
  },
  {
    value: "other",
    label: "Doanh nghiệp & Ngành nghề khác",
    icon: "✨",
    desc: "Thiết kế linh hoạt theo phong cách và giọng văn riêng biệt của thương hiệu bạn",
  },
];
