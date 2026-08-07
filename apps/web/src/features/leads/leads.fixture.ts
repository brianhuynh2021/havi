export type LeadReplyStatus =
  | "new"
  | "auto_replied"
  | "awaiting_approval"
  | "sent"
  | "booked";

export type Lead = {
  id: string;
  name: string;
  source: "Fanpage" | "Google Maps" | "Nhóm";
  message: string;
  suggestedReply: string;
  status: LeadReplyStatus;
  time: string;
};

export const leadsFixture: Lead[] = [
  {
    id: "lead-1",
    name: "Chị Mai",
    source: "Fanpage",
    message: "Cho em hỏi combo gội đầu thảo dược giá bao nhiêu ạ?",
    suggestedReply:
      "Chào chị Mai, combo gội đầu thảo dược hiện đang có giá 250K, cuối tuần này giảm 10% cho khách mới. Chị muốn đặt lịch ngày nào để tiệm giữ giờ cho chị ạ?",
    status: "awaiting_approval",
    time: "08:30",
  },
  {
    id: "lead-2",
    name: "Anh Tuấn",
    source: "Google Maps",
    message: "Tiệm còn nhận khách chiều thứ 7 không shop?",
    suggestedReply:
      "Chào anh Tuấn, chiều thứ 7 tiệm còn trống lịch 15h và 16h30 ạ. Anh chọn giờ nào để em giữ chỗ giúp anh?",
    status: "awaiting_approval",
    time: "10:14",
  },
  {
    id: "lead-3",
    name: "Chị Ngọc Anh",
    source: "Nhóm",
    message: "Giờ mở cửa tiệm là mấy giờ vậy?",
    suggestedReply: "Tiệm mở cửa 8h–20h các ngày trong tuần, kể cả Chủ nhật ạ.",
    status: "sent",
    time: "Hôm qua",
  },
];

export const faqStripFixture = [
  { id: "faq-1", question: "Giờ mở cửa?", answer: "8h–20h mỗi ngày" },
  { id: "faq-2", question: "Địa chỉ tiệm?", answer: "12 Nguyễn Trãi, Q.1" },
  { id: "faq-3", question: "Có giữ xe không?", answer: "Có bãi giữ xe miễn phí" },
];
