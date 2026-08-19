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
    desc: "Đăng món mới, menu bánh tươi mỗi ngày & giờ vàng kéo khách ghé quán",
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
    desc: "Bài xả kho, chào hàng đa kênh, video giới thiệu sản phẩm & chốt đơn",
  },
  {
    value: "education",
    label: "Giáo dục, Ngoại ngữ & Đào tạo nghề",
    icon: "🎓",
    desc: "Tuyển sinh khóa mới, khoe dự án học viên thực chiến & giải đáp học phí 24/7",
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
    desc: "Chụp ảnh sổ đỏ/nhà đất ra bài chuẩn phong thủy, kịch bản video TikTok 3s",
  },
  {
    value: "professional",
    label: "Dịch vụ chuyên môn & Tư vấn",
    icon: "⚖️",
    desc: "Khẳng định uy tín chuyên gia, chia sẻ kinh nghiệm & thu hút khách tư vấn",
  },
  {
    value: "other",
    label: "Doanh nghiệp & Ngành nghề khác",
    icon: "✨",
    desc: "Thiết kế linh hoạt theo phong cách và giọng văn riêng biệt của thương hiệu bạn",
  },
];
