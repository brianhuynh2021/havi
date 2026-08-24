"""AI Lead Intent Detection & Phone Extraction Policies."""

import re
from dataclasses import dataclass
from enum import StrEnum


class LeadIntentKind(StrEnum):
    PRICE_INQUIRY = "price_inquiry"  # Hỏi học phí, giá dịch vụ
    CURRICULUM = "curriculum_inquiry"  # Hỏi chương trình học, thời gian, giáo trình
    LOCATION = "location_inquiry"  # Hỏi địa chỉ, cơ sở, bản đồ
    ENROLLMENT = "enrollment_intent"  # Muốn đăng ký học, đặt chỗ, giữ suất
    GENERAL_SUPPORT = "general_support"  # Thắc mắc chung, chào hỏi


@dataclass
class LeadAnalysisResult:
    intent: LeadIntentKind
    confidence: float
    extracted_phone: str | None
    extracted_name: str | None
    suggested_tags: list[str]
    suggested_reply: str


# Regex chuẩn số điện thoại di động Việt Nam (10 chữ số bắt đầu bằng 03, 05, 07, 08, 09 hoặc +84)
VIETNAM_PHONE_REGEX = re.compile(r"(?:(?:\+84|84|0)[\s\.\-]?[35789])(?:[\s\.\-]?\d){8}\b")


def extract_vietnam_phone(text: str) -> str | None:
    """Trích xuất và chuẩn hóa số điện thoại di động Việt Nam từ văn bản."""
    if not text:
        return None
    match = VIETNAM_PHONE_REGEX.search(text)
    if not match:
        return None
    raw = match.group(0)
    # Chuẩn hóa về định dạng 10 chữ số bắt đầu bằng 0
    cleaned = re.sub(r"[^\d+]", "", raw)
    if cleaned.startswith("+84"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("84") and len(cleaned) == 11:
        cleaned = "0" + cleaned[2:]
    return cleaned if len(cleaned) == 10 and cleaned.startswith("0") else None


def classify_lead_intent(text: str, author_name: str = "") -> LeadAnalysisResult:
    """Phân loại ý định khách hàng/học viên và sinh câu trả lời tư vấn gợi ý."""
    lower = (text or "").lower()
    phone = extract_vietnam_phone(text)

    # Từ khóa nhận diện
    price_keywords = (
        "học phí",
        "bao nhiêu",
        "giá",
        "chi phí",
        "bao tiền",
        "hết bao nhiêu",
        "báo giá",
    )
    curriculum_keywords = (
        "học gì",
        "giáo trình",
        "mấy tháng",
        "thời gian học",
        "khóa học",
        "dạy những gì",
        "học nghề",
        "cấp tốc",
        "thực hành",
    )
    location_keywords = ("địa chỉ", "ở đâu", "chi nhánh", "cơ sở", "quận mấy", "trung tâm ở đâu")
    enrollment_keywords = (
        "đăng ký",
        "ghi danh",
        "nhập học",
        "giữ chỗ",
        "bắt đầu học",
        "khi nào khai giảng",
        "muốn học",
    )

    tags = []
    if phone:
        tags.append("#co_so_dien_thoai")

    if any(k in lower for k in enrollment_keywords):
        intent = LeadIntentKind.ENROLLMENT
        confidence = 0.95
        tags.append("#dang_ky_ngay")
        tags.append("#hot_lead")
        reply = f"Dạ Trung Tâm Công Nghệ Nhật Minh xin chào {author_name or 'anh/chị'}! Dạ khóa học thực chiến khai giảng hàng tuần với phương châm cầm tay chỉ việc trên máy thật. Em đã lưu thông tin của mình để thầy phụ trách liên hệ xếp lịch học sớm nhất cho mình nhé ạ!"
    elif any(k in lower for k in price_keywords):
        intent = LeadIntentKind.PRICE_INQUIRY
        confidence = 0.92
        tags.append("#hoi_hoc_phi")
        reply = f"Dạ em chào {author_name or 'anh/chị'}! Học phí các khóa nghề thực hành tại Trung Tâm Nhật Minh đã bao gồm trọn gói đồ nghề và linh kiện thực tập, cam kết không phát sinh. Anh/chị có thể để lại số Zalo để em gửi bảng học phí và ưu đãi tháng này cho mình nhé!"
    elif any(k in lower for k in curriculum_keywords):
        intent = LeadIntentKind.CURRICULUM
        confidence = 0.88
        tags.append("#hoi_giao_trinh")
        reply = f"Dạ em chào {author_name or 'anh/chị'}! Chương trình học tại Nhật Minh tập trung 80% thời lượng thực hành trực tiếp trên thiết bị và bo mạch thực tế. Anh/chị đang quan tâm khóa cấp tốc 3 tháng hay khóa chuyên sâu ạ?"
    elif any(k in lower for k in location_keywords):
        intent = LeadIntentKind.LOCATION
        confidence = 0.90
        tags.append("#hoi_dia_chi")
        reply = "Dạ Trung Tâm Công Nghệ Nhật Minh tọa lạc tại vị trí thuận tiện để học viên các quận đến thực hành trực tiếp mỗi ngày. Anh/chị có thể ghé trực tiếp trung tâm để tham quan phòng thực hành và trải nghiệm thử 1 buổi trước khi đăng ký ạ!"
    else:
        intent = LeadIntentKind.GENERAL_SUPPORT
        confidence = 0.75
        tags.append("#tu_van_chung")
        reply = f"Dạ Trung Tâm Công Nghệ Nhật Minh xin chào {author_name or 'anh/chị'}! Em có thể hỗ trợ thông tin gì về các khóa đào tạo nghề công nghệ thực chiến cho mình ạ?"

    return LeadAnalysisResult(
        intent=intent,
        confidence=confidence,
        extracted_phone=phone,
        extracted_name=author_name or None,
        suggested_tags=tags,
        suggested_reply=reply,
    )
