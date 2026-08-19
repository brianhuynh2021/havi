"""Domain Policy cho CRM Lifecycle Nudges (Chăm sóc khách cũ tự động).

Quy tắc kinh doanh:
1. Chỉ tạo nudge cho khách có số điện thoại hoặc tin nhắn đã từng chốt/hỏi (Stage WON hoặc CONTACTED/NEW).
2. Không gửi dồn dập (Anti-Spam): Mỗi khách chỉ nhận tối đa 1 nudge trong vòng 30 ngày.
3. Kịch bản cá nhân hóa theo ngành hàng (Spa, F&B, Salon, Khác) và kèm mã ưu đãi độc quyền.
"""

from datetime import datetime, timedelta

from core.enums import CrmNudgeType, Industry


def generate_nudge_message(
    lead_name: str,
    industry: Industry | str,
    nudge_type: CrmNudgeType = CrmNudgeType.INACTIVE_30_DAYS,
    brand_name: str = "Tiệm",
    discount_percent: int = 20,
) -> str:
    """Sinh tin nhắn chăm sóc cá nhân hóa theo ngành hàng."""
    ind_str = industry.value if isinstance(industry, Industry) else str(industry).lower()
    name = lead_name.strip() or "chị"

    if nudge_type == CrmNudgeType.FOLLOWUP_14_DAYS:
        if ind_str == "spa":
            return (
                f"Dạ {brand_name} chào {name} ạ! Đã 2 tuần từ buổi chăm sóc da vừa rồi, "
                f"da mình hôm nay thế nào rồi ạ? Chị nhớ dưỡng ẩm đều đặn nha!"
            )
        elif ind_str == "food_beverage":
            return (
                f"Chào {name} ơi! {brand_name} vừa ra mắt món mới trong tuần này. "
                f"Mời {name} ghé dùng thử nhận ngay ưu đãi giảm {discount_percent}% nhé!"
            )
        elif ind_str == "education":
            return (
                f"Chào {name} ạ! {brand_name} gửi lời hỏi thăm tình hình học tập và thực hành của mình. "
                f"Nếu cần thầy cô hỗ trợ thêm kiến thức gì, {name} cứ nhắn trung tâm nhé!"
            )
        elif ind_str == "local_service":
            return (
                f"Dạ {brand_name} chào {name} ạ! Sau 2 tuần trải nghiệm dịch vụ, "
                f"mình có cần hỗ trợ thêm thông tin hoặc hướng dẫn nào không ạ?"
            )
        elif ind_str in ("retail_shop", "online_shop"):
            return (
                f"Chào {name} ơi! Sản phẩm mình mua đợt trước dùng ưng ý không ạ? "
                f"Shop vừa về thêm bộ sưu tập mới, {name} ghé xem nhé!"
            )
        else:
            return (
                f"Chào {name} ạ! {brand_name} gửi lời hỏi thăm đến mình. "
                f"Nếu cần hỗ trợ thêm thông tin gì, chị cứ nhắn tiệm nhé!"
            )

    # Mặc định: INACTIVE_30_DAYS (Khách cũ 30 ngày chưa quay lại)
    if ind_str == "spa":
        return (
            f"Dạ {brand_name} chào {name} ạ! Đã tròn 1 tháng từ lần gần nhất chị ghé tiệm rồi đó ạ. "
            f"Đến kỳ chăm sóc và phục hồi da định kỳ rồi, tiệm tặng riêng {name} voucher giảm {discount_percent}% "
            f"khi đặt lịch trong tuần này nhé!"
        )
    elif ind_str == "food_beverage":
        return (
            f"Chào {name} thân thương! Lâu rồi chưa thấy {name} ghé {brand_name}. "
            f"Tiệm gửi tặng {name} mã voucher giảm {discount_percent}% cho lần ghé kế tiếp. "
            f"Hẹn sớm gặp lại {name} ạ!"
        )
    elif ind_str == "education":
        return (
            f"Chào {name} ạ! {brand_name} chuẩn bị khai giảng khóa chuyên sâu & cập nhật mới trong tháng này. "
            f"Trung tâm gửi tặng riêng {name} học bổng ưu đãi {discount_percent}% khi đăng ký sớm nha!"
        )
    elif ind_str == "local_service":
        return (
            f"Dạ {brand_name} chào {name} ạ! Đã 1 tháng từ lần giao dịch/thăm khám gần nhất. "
            f"Chi nhánh gửi tặng {name} mã ưu đãi đặc quyền giảm {discount_percent}% cho lần ghé tiếp theo ạ!"
        )
    elif ind_str in ("retail_shop", "online_shop"):
        return (
            f"Chào {name} thân thương! Shop vừa tung voucher tri ân giảm {discount_percent}% "
            f"dành riêng cho khách hàng thân thiết. Nhắn shop để nhận mã sắm đồ mới nha!"
        )
    else:
        return (
            f"Chào {name} ạ! {brand_name} rất nhớ mình sau 1 tháng vừa qua. "
            f"Tiệm xin gửi tặng {name} ưu đãi tri ân giảm {discount_percent}% cho dịch vụ tiếp theo. "
            f"Nhắn tiệm để nhận ưu đãi ngay nha!"
        )


def is_eligible_for_nudge(
    lead_created_at: datetime,
    last_nudged_at: datetime | None,
    now: datetime,
    min_days: int = 30,
) -> bool:
    """Kiểm tra điều kiện khách hàng có đủ điều kiện nhận tin nhắc hay không."""
    # Khách phải tạo trước ít nhất `min_days` ngày
    if now - lead_created_at < timedelta(days=min_days):
        return False

    # Nếu đã từng nhận nudge, phải cách ít nhất `min_days` ngày
    if last_nudged_at and (now - last_nudged_at < timedelta(days=min_days)):
        return False

    return True
