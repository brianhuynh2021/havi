"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client/client";
import { readTokens } from "@/lib/auth/token-store";
import {
  createGoal,
  generateRoadmap,
  type ActiveRoadmapData,
  type Goal,
  type GoalCategory,
} from "./roadmap.api";
import styles from "./roadmap.module.css";

export interface GoalTemplate {
  title: string;
  category: GoalCategory;
  evidence_definition: string;
  description: string;
  weekly_capacity_hours: number;
  icon: string;
  horizon_days: number;
}

export function formatHorizonLabel(days: number): string {
  if (days <= 0) return "7 ngày";
  if (days % 365 === 0) return `${days / 365} năm`;
  if (days % 30 === 0) return `${days / 30} tháng`;
  if (days % 7 === 0) return `${days / 7} tuần`;
  if (days >= 30) {
    const months = Math.round(days / 30);
    return `${months} tháng (~${days} ngày)`;
  }
  return `${days} ngày`;
}

export function getGoalTemplates(industry?: string, horizonDays: number = 30): GoalTemplate[] {
  const ind = (industry || "").toLowerCase();
  const days = Math.max(1, horizonDays || 30);
  const timeLabel = formatHorizonLabel(days);

  if (ind.includes("education") || ind.includes("giáo dục") || ind.includes("đào tạo") || ind.includes("ngoại ngữ")) {
    if (days === 7) {
      return [
        {
          title: "Tuyển sinh 5 học viên mới trong tuần này",
          category: "acquire_customers",
          evidence_definition: "Có ít nhất 5 học viên để lại thông tin tư vấn hoặc đăng ký học",
          description: "Tập trung tiếp cận nhanh phụ huynh/học viên địa phương trong 7 ngày.",
          weekly_capacity_hours: 6,
          icon: "🎓",
          horizon_days: 7,
        },
        {
          title: "Tổ chức lớp học thử / trải nghiệm cuối tuần này",
          category: "sell_offer",
          evidence_definition: "Có 10-15 người đăng ký tham gia lớp trải nghiệm cuối tuần",
          description: "Tạo sự kiện trải nghiệm thực tế để phụ huynh và học viên tin tưởng chất lượng.",
          weekly_capacity_hours: 5,
          icon: "💡",
          horizon_days: 7,
        },
        {
          title: "Xuất bản 3 video Reels bài học ngắn trong 7 ngày",
          category: "grow_audience",
          evidence_definition: "Đăng 3 video 9:16 chia sẻ mẹo học/bài học thực tế lên Facebook Reels",
          description: "Duy trì sự hiện diện và khẳng định uy tín chuyên môn của trung tâm.",
          weekly_capacity_hours: 6,
          icon: "🎬",
          horizon_days: 7,
        },
      ];
    }
    if (days === 14) {
      return [
        {
          title: "Tuyển sinh 10 học viên mới trong 2 tuần tới",
          category: "acquire_customers",
          evidence_definition: "Có ít nhất 10 học viên để lại thông tin tư vấn hoặc đăng ký",
          description: "Chiến dịch tuyển sinh ngắn hạn 14 ngày qua bài viết và video Reels.",
          weekly_capacity_hours: 8,
          icon: "🎓",
          horizon_days: 14,
        },
        {
          title: "Tổ chức chuỗi 2 buổi chuyên đề trải nghiệm",
          category: "sell_offer",
          evidence_definition: "Có 20 người đăng ký tham gia chuỗi chuyên đề",
          description: "Tăng tỷ lệ chuyển đổi học viên thật qua trải nghiệm học thử.",
          weekly_capacity_hours: 6,
          icon: "💡",
          horizon_days: 14,
        },
        {
          title: "Xuất bản 6 video Reels bài học thực tế trong 14 ngày",
          category: "grow_audience",
          evidence_definition: "Xuất bản 6 video ngắn 9:16 chia sẻ chuyên môn lên Facebook Reels",
          description: "Xây dựng tệp người theo dõi tiềm năng cho trung tâm.",
          weekly_capacity_hours: 8,
          icon: "🎬",
          horizon_days: 14,
        },
      ];
    }
    if (days === 30) {
      return [
        {
          title: "Tuyển sinh 20 học viên mới trong 30 ngày",
          category: "acquire_customers",
          evidence_definition: "Có ít nhất 20 học viên để lại thông tin tư vấn hoặc đăng ký khóa học",
          description: "Tăng trưởng số lượng học viên qua bài viết Facebook và video ngắn chia sẻ chuyên môn.",
          weekly_capacity_hours: 10,
          icon: "🎓",
          horizon_days: 30,
        },
        {
          title: "Tổ chức lớp học trải nghiệm thu hút 30 học viên",
          category: "sell_offer",
          evidence_definition: "Có 30 người đăng ký tham gia lớp học thử hoặc hội thảo chuyên đề",
          description: "Tạo sự kiện trải nghiệm thực tế để phụ huynh và học viên tin tưởng chất lượng đào tạo.",
          weekly_capacity_hours: 8,
          icon: "💡",
          horizon_days: 30,
        },
        {
          title: "Xây dựng thương hiệu với 10 video Reels bài học thực tế",
          category: "grow_audience",
          evidence_definition: "Xuất bản 10 video ngắn 9:16 chia sẻ kiến thức chuyên môn lên Facebook Reels",
          description: "Khẳng định uy tín chuyên môn của trung tâm qua các bài học ngắn súc tích, dễ hiểu.",
          weekly_capacity_hours: 12,
          icon: "🎬",
          horizon_days: 30,
        },
      ];
    }
    if (days === 90) {
      return [
        {
          title: "Tuyển sinh 60 học viên mới & mở rộng 3 lớp trong quý",
          category: "acquire_customers",
          evidence_definition: "Có 60 học viên chính thức nhập học các khóa đào tạo",
          description: "Chiến dịch tăng trưởng tuyển sinh quy mô quý cho trung tâm.",
          weekly_capacity_hours: 12,
          icon: "🎓",
          horizon_days: 90,
        },
        {
          title: "Tăng 50% doanh thu đào tạo từ các khóa nâng cao",
          category: "sell_offer",
          evidence_definition: "Doanh thu học phí ghi nhận từ các lớp chuyên sâu",
          description: "Tối ưu hóa giá trị mỗi học viên và tỷ lệ học lên khóa tiếp theo.",
          weekly_capacity_hours: 10,
          icon: "💰",
          horizon_days: 90,
        },
        {
          title: "Xây dựng kênh Facebook Reels với 30 video bài học",
          category: "grow_audience",
          evidence_definition: "Xuất bản đều đặn 30 video chuyên môn chất lượng cao",
          description: "Đưa trung tâm trở thành địa chỉ uy tín hàng đầu trong khu vực.",
          weekly_capacity_hours: 12,
          icon: "🎬",
          horizon_days: 90,
        },
      ];
    }
    if (days === 180) {
      return [
        {
          title: "Tuyển sinh 120 học viên & hoàn thiện hệ thống 5 lớp chuẩn",
          category: "acquire_customers",
          evidence_definition: "Đạt 120 học viên chính thức nhập học trong 6 tháng",
          description: "Mục tiêu mở rộng quy mô nửa năm của trung tâm.",
          weekly_capacity_hours: 12,
          icon: "🎓",
          horizon_days: 180,
        },
        {
          title: "Tăng gấp đôi doanh thu đào tạo & khóa chuyên sâu",
          category: "sell_offer",
          evidence_definition: "Doanh thu học phí tăng trưởng 100% so với 6 tháng trước",
          description: "Đa dạng hóa các khóa học nâng cao và tối ưu tỷ lệ tái tục học phí.",
          weekly_capacity_hours: 10,
          icon: "💰",
          horizon_days: 180,
        },
        {
          title: "Xây dựng kênh bài học uy tín với 60 video Facebook Reels",
          category: "grow_audience",
          evidence_definition: "Xuất bản 60 video ngắn chất lượng cao xây dựng thương hiệu số 1",
          description: "Tạo tệp phụ huynh & học viên theo dõi trung thành dài hạn.",
          weekly_capacity_hours: 12,
          icon: "🎬",
          horizon_days: 180,
        },
      ];
    }
    if (days === 270) {
      return [
        {
          title: "Tuyển sinh 180 học viên & định vị thương hiệu đào tạo 9 tháng",
          category: "acquire_customers",
          evidence_definition: "Đạt 180 học viên chính thức theo học trong 9 tháng",
          description: "Kế hoạch mở rộng tuyển sinh và nhân rộng các lớp học chất lượng cao.",
          weekly_capacity_hours: 12,
          icon: "🎓",
          horizon_days: 270,
        },
        {
          title: "Tăng 80% doanh thu đào tạo & phát triển các khóa học mũi nhọn",
          category: "sell_offer",
          evidence_definition: "Doanh thu học phí tăng 80% từ học viên mới và học viên gia hạn",
          description: "Gia tăng doanh thu ổn định và phát triển các chương trình đào tạo chuyên sâu.",
          weekly_capacity_hours: 10,
          icon: "💰",
          horizon_days: 270,
        },
        {
          title: "Phủ sóng thương hiệu với 80 video Facebook Reels bài học thực tế",
          category: "grow_audience",
          evidence_definition: "Xuất bản 80 video ngắn 9:16 chất lượng cao trên Facebook Reels",
          description: "Khẳng định trung tâm là điểm đến đào tạo tin cậy số 1 tại địa phương.",
          weekly_capacity_hours: 12,
          icon: "🎬",
          horizon_days: 270,
        },
      ];
    }
    if (days === 365) {
      return [
        {
          title: "Tuyển sinh 250 học viên & mở rộng cơ sở đào tạo trong 1 năm",
          category: "acquire_customers",
          evidence_definition: "Đạt mốc 250 học viên theo học trong năm",
          description: "Chiến lược tăng trưởng quy mô cả năm và mở thêm cơ sở/lớp mới.",
          weekly_capacity_hours: 12,
          icon: "🎓",
          horizon_days: 365,
        },
        {
          title: "Đạt chỉ tiêu doanh thu năm & tỷ lệ giữ chân học viên > 85%",
          category: "sell_offer",
          evidence_definition: "Doanh thu năm đạt chỉ tiêu và tỷ lệ học viên học tiếp đạt trên 85%",
          description: "Xây dựng mô hình trung tâm vận hành hiệu quả và bền vững.",
          weekly_capacity_hours: 10,
          icon: "💰",
          horizon_days: 365,
        },
        {
          title: "Kênh truyền thông 100 video chuyên môn uy tín số 1 khu vực",
          category: "grow_audience",
          evidence_definition: "Xuất bản 100 video Reels và bài viết chuyên môn định vị thương hiệu",
          description: "Đưa trung tâm trở thành đơn vị đào tạo uy tín hàng đầu khu vực.",
          weekly_capacity_hours: 12,
          icon: "🎬",
          horizon_days: 365,
        },
      ];
    }

    // Dynamic scale for arbitrary custom days
    const studentCount = Math.max(3, Math.round(days * 0.65));
    const videoCount = Math.max(2, Math.round(days * 0.25));
    return [
      {
        title: `Tuyển sinh ${studentCount} học viên mới trong ${timeLabel}`,
        category: "acquire_customers",
        evidence_definition: `Có ít nhất ${studentCount} học viên tư vấn hoặc đăng ký học trong ${timeLabel}`,
        description: `Chiến lược tuyển sinh và mở rộng lớp học trong ${timeLabel}.`,
        weekly_capacity_hours: 10,
        icon: "🎓",
        horizon_days: days,
      },
      {
        title: `Tăng trưởng doanh thu đào tạo và lớp học nâng cao trong ${timeLabel}`,
        category: "sell_offer",
        evidence_definition: `Doanh thu học phí ghi nhận đạt mục tiêu trong ${timeLabel}`,
        description: `Tối ưu hóa giá trị học viên và mở rộng các khóa học mới trong ${timeLabel}.`,
        weekly_capacity_hours: 8,
        icon: "💰",
        horizon_days: days,
      },
      {
        title: `Xây dựng thương hiệu uy tín với ${videoCount} video Facebook Reels`,
        category: "grow_audience",
        evidence_definition: `Xuất bản ${videoCount} video ngắn 9:16 chia sẻ chuyên môn trong ${timeLabel}`,
        description: `Định vị uy tín chuyên môn của trung tâm tại địa phương trong ${timeLabel}.`,
        weekly_capacity_hours: 12,
        icon: "🎬",
        horizon_days: days,
      },
    ];
  }

  if (ind.includes("restaurant") || ind.includes("fnb") || ind.includes("ăn uống") || ind.includes("cà phê") || ind.includes("bánh")) {
    if (days === 7) {
      return [
        {
          title: "Kéo 15 lượt thực khách mới ghé quán tuần này",
          category: "acquire_customers",
          evidence_definition: "Có ít nhất 15 lượt đặt bàn hoặc check-in mới",
          description: "Quảng bá món đặc sắc kéo khách trong 7 ngày tới.",
          weekly_capacity_hours: 6,
          icon: "🍽️",
          horizon_days: 7,
        },
        {
          title: "Ra mắt combo ưu đãi giờ vàng trong tuần",
          category: "sell_offer",
          evidence_definition: "Doanh thu ghi nhận từ combo ưu đãi trong 7 ngày",
          description: "Kích thích thực khách ghé vào khung giờ vắng khách.",
          weekly_capacity_hours: 5,
          icon: "💰",
          horizon_days: 7,
        },
        {
          title: "Đăng 3 video Reels cận cảnh món ngon tuần này",
          category: "grow_audience",
          evidence_definition: "Xuất bản 3 video ngắn 9:16 quay món ăn lên Facebook Reels",
          description: "Tăng tương tác và kích thích vị giác của thực khách địa phương.",
          weekly_capacity_hours: 6,
          icon: "🎬",
          horizon_days: 7,
        },
      ];
    }
    const customerCount = days <= 14 ? "25" : days <= 30 ? "50" : days <= 90 ? "150" : days <= 180 ? "300" : days <= 270 ? "500" : `${Math.round(days * 1.5)}`;
    const videoCount = days <= 14 ? "5" : days <= 30 ? "10" : days <= 90 ? "30" : days <= 180 ? "60" : days <= 270 ? "80" : "100";
    return [
      {
        title: `Kéo ${customerCount} lượt thực khách mới ghé quán trong ${timeLabel}`,
        category: "acquire_customers",
        evidence_definition: `Có ít nhất ${customerCount} lượt đặt bàn, check-in hoặc hỏi menu`,
        description: `Quảng bá món đặc trưng và không gian quán đến thực khách địa phương trong ${timeLabel}.`,
        weekly_capacity_hours: 10,
        icon: "🍽️",
        horizon_days: days,
      },
      {
        title: `Tăng 30% doanh thu bằng combo món mới & chăm sóc khách quen`,
        category: "sell_offer",
        evidence_definition: "Doanh thu ghi nhận từ khách gọi combo hoặc khách quen quay lại",
        description: "Thúc đẩy doanh thu bền vững bằng chương trình tri ân và món mới.",
        weekly_capacity_hours: 8,
        icon: "💰",
        horizon_days: days,
      },
      {
        title: `Quảng bá thương hiệu ẩm thực với ${videoCount} video Facebook Reels`,
        category: "grow_audience",
        evidence_definition: `Xuất bản ${videoCount} video ngắn 9:16 quay cận cảnh món ngon`,
        description: "Kích thích vị giác và thị giác của thực khách địa phương bằng video chân thực.",
        weekly_capacity_hours: 12,
        icon: "🎬",
        horizon_days: days,
      },
    ];
  }

  // Spa / Làm đẹp
  if (ind.includes("spa") || ind.includes("beauty") || ind.includes("làm đẹp") || ind.includes("salon")) {
    if (days === 7) {
      return [
        {
          title: "Thu hút 5 khách hàng mới trải nghiệm tuần này",
          category: "acquire_customers",
          evidence_definition: "Có ít nhất 5 khách đặt lịch hẹn liệu trình đầu tiên",
          description: "Ưu đãi trải nghiệm kéo khách mới trong tuần.",
          weekly_capacity_hours: 6,
          icon: "✨",
          horizon_days: 7,
        },
        {
          title: "Nhắc lịch & gửi ưu đãi tri ân 10 khách hàng cũ",
          category: "sell_offer",
          evidence_definition: "Có khách quen đặt lịch quay lại làm dịch vụ trong tuần",
          description: "Chăm sóc khách hàng cũ gia tăng doanh thu tức thì.",
          weekly_capacity_hours: 5,
          icon: "💰",
          horizon_days: 7,
        },
        {
          title: "Đăng 3 video Reels khoe tay nghề và dịch vụ thực tế",
          category: "grow_audience",
          evidence_definition: "Xuất bản 3 video ngắn kết quả trước & sau khi làm đẹp",
          description: "Khẳng định chất lượng dịch vụ và tay nghề uy tín.",
          weekly_capacity_hours: 6,
          icon: "🎬",
          horizon_days: 7,
        },
      ];
    }
    const spaCount = days <= 14 ? "10" : days <= 30 ? "20" : days <= 90 ? "60" : days <= 180 ? "150" : days <= 270 ? "220" : `${Math.round(days * 0.8)}`;
    const spaVideo = days <= 14 ? "5" : days <= 30 ? "10" : days <= 90 ? "30" : days <= 180 ? "60" : days <= 270 ? "80" : "100";
    return [
      {
        title: `Thu hút ${spaCount} khách hàng mới trải nghiệm trong ${timeLabel}`,
        category: "acquire_customers",
        evidence_definition: `Có ít nhất ${spaCount} khách đặt lịch hẹn hoặc nhắn tin tư vấn`,
        description: `Tăng lượng khách mới bằng bài viết dịch vụ và ưu đãi trong ${timeLabel}.`,
        weekly_capacity_hours: 10,
        icon: "✨",
        horizon_days: days,
      },
      {
        title: "Tăng 30% doanh thu bằng liệu trình chăm sóc khách quen",
        category: "sell_offer",
        evidence_definition: "Doanh thu ghi nhận từ khách hàng quen quay lại sử dụng dịch vụ",
        description: "Gửi tin nhắn ưu đãi tri ân và nhắc lịch chăm sóc định kỳ cho khách hàng cũ.",
        weekly_capacity_hours: 8,
        icon: "💰",
        horizon_days: days,
      },
      {
        title: `Xây dựng uy tín tay nghề với ${spaVideo} video Facebook Reels`,
        category: "grow_audience",
        evidence_definition: `Xuất bản ${spaVideo} video ngắn kết quả thực tế`,
        description: "Tạo niềm tin vững chắc cho khách hàng bằng tay nghề thực tế và sự tận tâm.",
        weekly_capacity_hours: 12,
        icon: "🎬",
        horizon_days: days,
      },
    ];
  }

  // Phổ quát / Bán lẻ / Khác
  if (days === 7) {
    return [
      {
        title: "Thu hút 5 khách hàng tiềm năng mới trong 7 ngày",
        category: "acquire_customers",
        evidence_definition: "Có ít nhất 5 khách hàng để lại số điện thoại hoặc nhắn tin",
        description: "Tập trung tiếp cận nhanh khách hàng địa phương trong tuần.",
        weekly_capacity_hours: 6,
        icon: "🎯",
        horizon_days: 7,
      },
      {
        title: "Gửi ưu đãi tri ân kích cầu doanh thu tuần này",
        category: "sell_offer",
        evidence_definition: "Doanh thu ghi nhận từ khách hàng phản hồi ưu đãi tuần",
        description: "Chăm sóc khách hàng cũ và kéo doanh thu ngắn hạn.",
        weekly_capacity_hours: 5,
        icon: "💰",
        horizon_days: 7,
      },
      {
        title: "Xuất bản 3 video Facebook Reels chia sẻ thực tế",
        category: "grow_audience",
        evidence_definition: "Xuất bản 3 video ngắn 9:16 có kịch bản lên Facebook Reels",
        description: "Tạo sự hiện diện thương hiệu liên tục trong tuần.",
        weekly_capacity_hours: 6,
        icon: "🎬",
        horizon_days: 7,
      },
    ];
  }

  const genCount = days <= 14 ? "10" : days <= 30 ? "20" : days <= 90 ? "60" : days <= 180 ? "150" : days <= 270 ? "220" : `${Math.round(days * 0.8)}`;
  const genVideo = days <= 14 ? "5" : days <= 30 ? "10" : days <= 90 ? "30" : days <= 180 ? "60" : days <= 270 ? "80" : "100";

  return [
    {
      title: `Thu hút ${genCount} khách hàng tiềm năng mới trong ${timeLabel}`,
      category: "acquire_customers",
      evidence_definition: `Có ít nhất ${genCount} khách hàng để lại SĐT hoặc nhắn tin`,
      description: `Tăng trưởng số lượng khách hàng mới trong ${timeLabel} qua bài viết Facebook và video ngắn.`,
      weekly_capacity_hours: 10,
      icon: "🎯",
      horizon_days: days,
    },
    {
      title: "Tăng 30% doanh thu bằng ưu đãi chăm sóc khách hàng cũ",
      category: "sell_offer",
      evidence_definition: "Doanh thu ghi nhận từ khách hàng quay lại mua sắm / sử dụng dịch vụ",
      description: "Gửi tin nhắn ưu đãi tri ân khách cũ và đo lường lượng khách quay lại.",
      weekly_capacity_hours: 8,
      icon: "💰",
      horizon_days: days,
    },
    {
      title: `Xây dựng thương hiệu với ${genVideo} video Facebook Reels`,
      category: "grow_audience",
      evidence_definition: `Xuất bản ${genVideo} video ngắn 9:16 lên Facebook Reels`,
      description: "Tạo sự hiện diện mạnh mẽ tại địa phương bằng các nội dung chia sẻ thực tế.",
      weekly_capacity_hours: 12,
      icon: "🎬",
      horizon_days: days,
    },
  ];
}

export function getGoalPlaceholders(industry?: string, horizonDays: number = 30) {
  const ind = (industry || "").toLowerCase();
  const days = Math.max(1, horizonDays || 30);
  const timeLabel = formatHorizonLabel(days);
  const count = days <= 7 ? "5" : days <= 14 ? "10" : days <= 30 ? "20" : days <= 90 ? "60" : days <= 180 ? "120" : days <= 270 ? "180" : `${Math.round(days * 0.65)}`;

  if (ind.includes("education") || ind.includes("giáo dục") || ind.includes("đào tạo")) {
    return {
      title: `VD: Tuyển sinh ${count} học viên mới trong ${timeLabel}`,
      evidence: `VD: Có ${count} học viên để lại thông tin tư vấn hoặc đăng ký khóa học`,
    };
  }
  if (ind.includes("restaurant") || ind.includes("fnb") || ind.includes("ăn uống")) {
    const diner = days <= 7 ? "15" : days <= 14 ? "25" : days <= 30 ? "50" : days <= 90 ? "150" : days <= 180 ? "300" : days <= 270 ? "500" : "1.000";
    return {
      title: `VD: Kéo ${diner} lượt thực khách mới trong ${timeLabel}`,
      evidence: `VD: Có ${diner} lượt đặt bàn, check-in hoặc hỏi menu`,
    };
  }
  if (ind.includes("clinic") || ind.includes("y tế") || ind.includes("phòng khám")) {
    return {
      title: `VD: Thu hút ${count} bệnh nhân / khách hàng mới trong ${timeLabel}`,
      evidence: `VD: Có ${count} khách hàng đặt lịch khám qua Fanpage`,
    };
  }
  if (ind.includes("spa") || ind.includes("beauty") || ind.includes("làm đẹp")) {
    return {
      title: `VD: Thu hút ${count} khách hàng mới trải nghiệm trong ${timeLabel}`,
      evidence: `VD: Có ${count} khách đặt lịch hẹn hoặc nhắn tin tư vấn`,
    };
  }
  return {
    title: `VD: Thu hút ${count} khách hàng tiềm năng mới trong ${timeLabel}`,
    evidence: `VD: Có ${count} khách hàng để lại SĐT hoặc nhắn tin hỏi dịch vụ`,
  };
}

interface GoalCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGoalCreated: (goal: Goal, roadmapData?: ActiveRoadmapData) => void;
  industry?: string;
}

export function GoalCreateModal({ isOpen, onClose, onGoalCreated, industry: initialIndustry }: GoalCreateModalProps) {
  const [industry, setIndustry] = useState<string>(initialIndustry || "spa");
  const [activeTab, setActiveTab] = useState<"templates" | "custom">("templates");
  const [selectedHorizon, setSelectedHorizon] = useState<number>(7);
  const [isCustomHorizonOpen, setIsCustomHorizonOpen] = useState(false);
  const [customHorizonValue, setCustomHorizonValue] = useState(9);
  const [customHorizonUnit, setCustomHorizonUnit] = useState<"days" | "weeks" | "months" | "years">("months");
  const [selectedTemplate, setSelectedTemplate] = useState<number>(0);
  const [customTitle, setCustomTitle] = useState("");
  const [customEvidence, setCustomEvidence] = useState("");
  const [customCapacity, setCustomCapacity] = useState(6);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Tự động đọc industry của workspace đang hoạt động
  useEffect(() => {
    if (initialIndustry) {
      setIndustry(initialIndustry);
      return;
    }
    const activeId = readTokens()?.activeWorkspaceId;
    apiClient
      .GET("/workspaces")
      .then(({ data }) => {
        if (!data) return;
        const list = data as Array<{ id: string; industry: string }>;
        const active = list.find((w) => w.id === activeId) ?? list[0];
        if (active?.industry) {
          setIndustry(active.industry);
        }
      })
      .catch(() => {});
  }, [initialIndustry, isOpen]);

  const templates = useMemo(() => getGoalTemplates(industry, selectedHorizon), [industry, selectedHorizon]);
  const placeholders = useMemo(() => getGoalPlaceholders(industry, selectedHorizon), [industry, selectedHorizon]);

  const calculatedCustomDays = useMemo(() => {
    let d = customHorizonValue;
    if (customHorizonUnit === "weeks") d = customHorizonValue * 7;
    if (customHorizonUnit === "months") d = customHorizonValue * 30;
    if (customHorizonUnit === "years") d = customHorizonValue * 365;
    return Math.max(1, d);
  }, [customHorizonValue, customHorizonUnit]);

  if (!isOpen) return null;

  const handleApplyCustomHorizon = (days: number) => {
    const validDays = Math.max(1, days);
    setSelectedHorizon(validDays);
    setSelectedTemplate(0);
    if (activeTab === "custom") {
      const p = getGoalPlaceholders(industry, validDays);
      setCustomTitle(p.title.replace("VD: ", ""));
      setCustomEvidence(p.evidence.replace("VD: ", ""));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    let title = "";
    let evidence_definition = "";
    let category: GoalCategory = "acquire_customers";
    let description = "";
    let weekly_capacity_hours = customCapacity;

    if (activeTab === "templates" && templates[selectedTemplate]) {
      const t = templates[selectedTemplate];
      title = t.title;
      evidence_definition = t.evidence_definition;
      category = t.category;
      description = t.description;
      weekly_capacity_hours = t.weekly_capacity_hours;
    } else {
      title = customTitle.trim();
      evidence_definition = customEvidence.trim();
      category = "acquire_customers";
      description = `Mục tiêu tuỳ chỉnh theo nhu cầu riêng trong ${formatHorizonLabel(selectedHorizon)}.`;
      weekly_capacity_hours = customCapacity;
    }

    if (!title) {
      setError("Vui lòng nhập tên mục tiêu");
      setIsSubmitting(false);
      return;
    }

    if (!evidence_definition) {
      setError("Vui lòng nêu rõ kết quả mong muốn đạt được");
      setIsSubmitting(false);
      return;
    }

    // 1. Tạo Goal trên Backend
    const goalRes = await createGoal({
      title,
      category,
      evidence_definition,
      description,
      weekly_capacity_hours,
    });

    if (!goalRes.ok) {
      setError(goalRes.message);
      setIsSubmitting(false);
      return;
    }

    // 2. Tự động sinh Lộ trình & Việc hôm nay ngay lập tức
    const roadmapRes = await generateRoadmap(goalRes.data.id);
    setIsSubmitting(false);

    onGoalCreated(goalRes.data, roadmapRes.ok ? roadmapRes.data : undefined);
    onClose();
  };

  const mainHorizonPresets = [
    { days: 7, label: "⚡ 7 ngày" },
    { days: 14, label: "🚀 14 ngày" },
    { days: 30, label: "🎯 30 ngày (1 tháng)" },
    { days: 90, label: "📈 3 tháng (90 ngày)" },
  ];

  const extendedHorizonPresets = [
    { days: 180, label: "🏆 6 tháng", val: 6, unit: "months" as const },
    { days: 270, label: "🎖️ 9 tháng", val: 9, unit: "months" as const },
    { days: 365, label: "🌟 1 năm", val: 1, unit: "years" as const },
  ];

  return (
    <div className={styles.modalOverlay} role="dialog" aria-modal="true">
      <div className={styles.modalContent}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h3 className={styles.modalTitle}>🎯 Thiết Lập Mục Tiêu Tăng Trưởng</h3>
            <p style={{ fontSize: "13.5px", color: "var(--text-secondary)", margin: "4px 0 0" }}>
              Havi sẽ đồng hành và chia nhỏ mục tiêu thành từng việc nhẹ nhàng mỗi ngày.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "rgba(100, 116, 139, 0.1)",
              border: "none",
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              fontSize: "15px",
              cursor: "pointer",
              color: "var(--text-secondary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            aria-label="Đóng"
          >
            ✕
          </button>
        </div>

        {/* Tab Toggle */}
        <div className={styles.tabContainer}>
          <button
            type="button"
            className={`${styles.tabButton} ${activeTab === "templates" ? styles.tabButtonActive : ""}`}
            onClick={() => setActiveTab("templates")}
          >
            ✨ Gợi ý theo ngành (1 chạm)
          </button>
          <button
            type="button"
            className={`${styles.tabButton} ${activeTab === "custom" ? styles.tabButtonActive : ""}`}
            onClick={() => {
              setActiveTab("custom");
              if (!customTitle && templates[selectedTemplate]) {
                setCustomTitle(templates[selectedTemplate].title);
                setCustomEvidence(templates[selectedTemplate].evidence_definition);
                setCustomCapacity(templates[selectedTemplate].weekly_capacity_hours);
              }
            }}
          >
            ✍️ Tự nhập mục tiêu riêng
          </button>
        </div>

        {/* Horizon Selector Section */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", background: "#f8fafc", padding: "10px 14px", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "6px" }}>
            <span style={{ fontSize: "13px", fontWeight: 700, color: "#0f172a" }}>
              ⏱️ Khung thời gian: <span style={{ color: "#2563eb" }}>{formatHorizonLabel(selectedHorizon)}</span>
            </span>
            <button
              type="button"
              onClick={() => setIsCustomHorizonOpen(!isCustomHorizonOpen)}
              style={{
                background: isCustomHorizonOpen ? "#dbeafe" : "#ffffff",
                border: isCustomHorizonOpen ? "1.5px solid #2563eb" : "1px solid #94a3b8",
                padding: "4px 10px",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: 700,
                color: isCustomHorizonOpen ? "#1d4ed8" : "#1e293b",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              ⚙️ {isCustomHorizonOpen ? "Đóng tùy chỉnh" : "Tùy chỉnh khác..."}
            </button>
          </div>

          {/* Clean Main Presets */}
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {mainHorizonPresets.map((h) => {
              const isSelected = selectedHorizon === h.days && !isCustomHorizonOpen;
              return (
                <button
                  key={h.days}
                  type="button"
                  onClick={() => {
                    setIsCustomHorizonOpen(false);
                    handleApplyCustomHorizon(h.days);
                  }}
                  style={{
                    padding: "5px 12px",
                    borderRadius: "16px",
                    border: isSelected ? "2px solid #2563eb" : "1px solid #cbd5e1",
                    background: isSelected ? "#eff6ff" : "#ffffff",
                    color: isSelected ? "#1d4ed8" : "#475569",
                    fontWeight: 700,
                    fontSize: "12px",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  {h.label}
                </button>
              );
            })}
          </div>

          {/* Custom Horizon Drawer */}
          {isCustomHorizonOpen && (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "4px", padding: "12px 14px", background: "#ffffff", borderRadius: "10px", border: "1.5px solid #93c5fd" }}>
              {/* Extended presets (6 months, 9 months, 1 year) */}
              <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                <span style={{ fontSize: "12px", fontWeight: 600, color: "#64748b" }}>Mốc dài hạn:</span>
                {extendedHorizonPresets.map((h) => {
                  const isSelected = selectedHorizon === h.days;
                  return (
                    <button
                      key={h.days}
                      type="button"
                      onClick={() => {
                        handleApplyCustomHorizon(h.days);
                        setCustomHorizonValue(h.val);
                        setCustomHorizonUnit(h.unit);
                      }}
                      style={{
                        padding: "4px 12px",
                        borderRadius: "14px",
                        border: isSelected ? "2px solid #2563eb" : "1px solid #cbd5e1",
                        background: isSelected ? "#eff6ff" : "#ffffff",
                        color: isSelected ? "#1d4ed8" : "#475569",
                        fontWeight: 700,
                        fontSize: "11.5px",
                        cursor: "pointer",
                      }}
                    >
                      {h.label} {isSelected ? "✓" : ""}
                    </button>
                  );
                })}
              </div>

              {/* Custom Number Input with Explicit Apply Button */}
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", borderTop: "1px dashed #cbd5e1", paddingTop: "10px" }}>
                <span style={{ fontSize: "12px", fontWeight: 600, color: "#334155" }}>Hoặc tự nhập số lượng:</span>
                <input
                  type="number"
                  min={1}
                  max={3650}
                  value={customHorizonValue}
                  onChange={(e) => {
                    const val = Math.max(1, Number(e.target.value) || 1);
                    setCustomHorizonValue(val);
                  }}
                  style={{
                    width: "65px",
                    padding: "5px 8px",
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "13px",
                    fontWeight: 700,
                    color: "#0f172a",
                    background: "#f8fafc",
                  }}
                />
                <select
                  value={customHorizonUnit}
                  onChange={(e) => {
                    const unit = e.target.value as "days" | "weeks" | "months" | "years";
                    setCustomHorizonUnit(unit);
                  }}
                  style={{
                    padding: "5px 8px",
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "12px",
                    fontWeight: 700,
                    color: "#0f172a",
                    background: "#f8fafc",
                  }}
                >
                  <option value="days">Ngày</option>
                  <option value="weeks">Tuần</option>
                  <option value="months">Tháng</option>
                  <option value="years">Năm</option>
                </select>
                <span style={{ fontSize: "12px", color: "#64748b" }}>
                  = <strong style={{ color: "#2563eb" }}>{calculatedCustomDays} ngày</strong> ({formatHorizonLabel(calculatedCustomDays)})
                </span>

                <button
                  type="button"
                  onClick={() => {
                    handleApplyCustomHorizon(calculatedCustomDays);
                    setIsCustomHorizonOpen(false);
                  }}
                  style={{
                    marginLeft: "auto",
                    padding: "6px 14px",
                    background: selectedHorizon === calculatedCustomDays ? "#10b981" : "#2563eb",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: "8px",
                    fontSize: "12px",
                    fontWeight: 700,
                    cursor: "pointer",
                    boxShadow: "0 1px 2px rgba(0,0,0,0.08)",
                    transition: "all 0.15s ease",
                  }}
                >
                  {selectedHorizon === calculatedCustomDays ? "✓ Đang áp dụng" : "🚀 Áp dụng mốc này"}
                </button>
              </div>
            </div>
          )}
        </div>

        {error ? (
          <div style={{ background: "#fee2e2", color: "#991b1b", padding: "12px 14px", borderRadius: "10px", fontSize: "13.5px", fontWeight: 600 }}>
            {error}
          </div>
        ) : null}



        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
          {activeTab === "templates" ? (
            /* Templates View */
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {templates.map((t, idx) => {
                const isSelected = selectedTemplate === idx;
                return (
                  <div
                    key={t.title}
                    onClick={() => setSelectedTemplate(idx)}
                    className={`${styles.templateCard} ${isSelected ? styles.templateCardSelected : ""}`}
                  >
                    <span style={{ fontSize: "24px", lineHeight: 1 }}>{t.icon}</span>
                    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "4px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <strong style={{ fontSize: "15px", color: isSelected ? "#1d4ed8" : "#0f172a" }}>
                          {t.title}
                        </strong>
                        {isSelected ? (
                          <span style={{ color: "#2563eb", fontWeight: 800, fontSize: "16px" }}>✓</span>
                        ) : null}
                      </div>
                      <span style={{ fontSize: "13px", color: "#475569" }}>
                        📌 <strong>Kết quả:</strong> {t.evidence_definition}
                      </span>
                      <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                        <span style={{ fontSize: "11.5px", fontWeight: 700, background: "#dbeafe", color: "#1e40af", padding: "2px 8px", borderRadius: "4px" }}>
                          ⏱️ ~{t.weekly_capacity_hours} giờ/tuần
                        </span>
                        <span style={{ fontSize: "11.5px", fontWeight: 700, background: "#d1fae5", color: "#065f46", padding: "2px 8px", borderRadius: "4px" }}>
                          🎯 Kế hoạch 30 ngày
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* Custom Form View */
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>Tên mục tiêu cụ thể:</label>
                <input
                  type="text"
                  required
                  className={styles.input}
                  placeholder={placeholders.title}
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                />
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>Kết quả mong muốn đạt được (Khi nào coi là đạt?):</label>
                <textarea
                  required
                  rows={2}
                  className={styles.textarea}
                  placeholder={placeholders.evidence}
                  value={customEvidence}
                  onChange={(e) => setCustomEvidence(e.target.value)}
                />
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>Thời gian bạn có thể dành mỗi tuần:</label>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                  {[5, 10, 15, 20].map((hours) => (
                    <button
                      key={hours}
                      type="button"
                      onClick={() => setCustomCapacity(hours)}
                      style={{
                        padding: "6px 14px",
                        borderRadius: "8px",
                        border: customCapacity === hours ? "2px solid #2563eb" : "1px solid #cbd5e1",
                        background: customCapacity === hours ? "#eff6ff" : "#ffffff",
                        color: customCapacity === hours ? "#1d4ed8" : "#334155",
                        fontWeight: 700,
                        fontSize: "13px",
                        cursor: "pointer",
                      }}
                    >
                      {hours} giờ / tuần
                    </button>
                  ))}
                  <div style={{ display: "flex", alignItems: "center", gap: "4px", marginLeft: "4px" }}>
                    <input
                      type="number"
                      min={1}
                      max={80}
                      className={styles.input}
                      style={{ width: "70px", padding: "6px 10px", fontSize: "13px" }}
                      value={customCapacity}
                      onChange={(e) => setCustomCapacity(Number(e.target.value) || 10)}
                    />
                    <span style={{ fontSize: "12.5px", color: "#64748b" }}>giờ</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Action Footer */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px", paddingTop: "12px", borderTop: "1px solid #e2e8f0" }}>
            <Button variant="outline" type="button" onClick={onClose}>
              Huỷ
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting} style={{ padding: "10px 20px", fontWeight: 700 }}>
              {isSubmitting
                ? "⚡ Đang khởi tạo lộ trình..."
                : activeTab === "templates"
                ? "🚀 Bắt Đầu Kế Hoạch Với Mục Tiêu Này"
                : "🚀 Khởi Tạo Lộ Trình Ngay"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

