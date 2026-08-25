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

export type IndustryPreviewSample = {
  text: string;
  hashtags: string[];
};

export function toHashtagSlug(name: string, fallback: string = "Havi"): string {
  const cleaned = name.trim().replace(/[^\p{L}\p{N}]+/gu, "");
  return cleaned ? `#${cleaned}` : `#${fallback}`;
}

export function getIndustrySamplePreview(
  industry: IndustryOption["value"] | null,
  rawName: string,
): IndustryPreviewSample {
  const name = rawName.trim() || "thương hiệu của bạn";
  const tag = toHashtagSlug(rawName, "Havi");

  switch (industry) {
    case "education":
      return {
        text: `Khai giảng khóa mới tuần này tại ${name}! Tặng học bổng 15% & lộ trình học thực chiến cho 5 bạn học viên đầu tiên nhắn tin đăng ký...`,
        hashtags: [tag, "#TuyenSinhKhoaMoi", "#DaoTaoNgheThucChien"],
      };
    case "food_beverage":
      return {
        text: `Thưởng thức menu món mới đậm vị tuần này tại ${name}! Tặng ngay voucher giảm 15% cho khách hàng nhắn tin đặt bàn trước...`,
        hashtags: [tag, "#MonNgonMoiNgay", "#UuDaiTuanNay"],
      };
    case "retail_shop":
    case "online_shop":
      return {
        text: `Bộ sưu tập mới siêu hot đã cập bến ${name}! Tuần này xả kho ưu đãi 15% cho 10 đơn hàng đầu tiên nhắn tin chốt đơn...`,
        hashtags: [tag, "#ThoiTrangHot", "#SaleKhung"],
      };
    case "real_estate":
      return {
        text: `${name} giới thiệu quỹ căn theo thông tin chủ nhà cung cấp. Nhắn tin để nhân viên xác minh bảng giá, pháp lý và lịch xem nhà.`,
        hashtags: [tag, "#BatDongSan", "#NhaDatChinhChu"],
      };
    case "local_service":
      return {
        text: `${name} hân hạnh phục vụ quý khách với dịch vụ chuyên nghiệp & tận tâm! Đặt lịch hẹn trước ngay hôm nay để nhận ưu đãi đặc biệt...`,
        hashtags: [tag, "#DichVuTanTam", "#UuDaiKhaiTruong"],
      };
    case "professional":
      return {
        text: `${name} đồng hành cùng bạn với giải pháp tư vấn chuyên sâu & tối ưu chi phí! Đăng ký lịch tư vấn 1-1 miễn phí ngay tuần này...`,
        hashtags: [tag, "#TuVanChuyenNghiep", "#GiaiPhapToiUu"],
      };
    case "spa":
      return {
        text: `Hân hoan chào đón quý khách ghé thăm ${name}! Tuần này ưu đãi tặng voucher 15% liệu trình cho 5 khách hàng đầu tiên nhắn tin đặt lịch trước...`,
        hashtags: [tag, "#LamDepMoiNgay", "#ChamSocDa"],
      };
    case "other":
    default:
      return {
        text: `Hân hoan chào đón quý khách ghé thăm ${name}! Tuần này ưu đãi tặng voucher 15% cho 5 khách hàng đầu tiên nhắn tin kết nối...`,
        hashtags: [tag, "#UuDaiTuanNay", "#ChamSocKhachHang"],
      };
  }
}
