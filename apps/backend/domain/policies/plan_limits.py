"""Giới hạn theo gói — thứ khách hàng thật sự mua khi trả thêm tiền.

Vấn đề mà file này giải
-----------------------
Trước đó **quota token là gate duy nhất theo gói**. Mọi thứ khác — phân quyền
theo vai, báo cáo, nhiều thương hiệu — đều có ở mọi gói, kể cả gói dùng thử. Bảng
giá thì bán chúng như tính năng của gói cao hơn.

Hệ quả: thang giá của Havi thực chất là một **thang token**, tức là Havi vẫn đang
được định giá như một công cụ viết nội dung bằng AI — đúng cái định vị vừa bị gỡ
khỏi sản phẩm. Người dùng không có lý do nâng gói ngoài việc đụng tường token.

Định giá theo quy mô vận hành
-----------------------------
Havi là chỗ ngồi làm việc của người trực kênh. Cái lớn lên theo doanh nghiệp là:

- **số người dùng** — resort có 3 nhân viên trực ca, chuỗi có 20;
- **số kênh nối** — một Trang, rồi thêm TikTok, YouTube;
- **số thương hiệu** — một cơ sở, rồi chuỗi nhiều chi nhánh.

Ba thứ đó vừa là nơi giá trị tăng, vừa là nơi chi phí tăng, nên chúng là thang
giá đúng. Quota token ở `quota.py` giữ vai trò khác: **chặn chi phí LLM**, không
phải bán hàng.

Vì sao có đòn bẩy mở rộng doanh thu mới quan trọng: bậc giá cố định thì một khách
lớn lên từ 1 lên 10 chi nhánh vẫn trả đúng một giá, và net revenue retention bị
chặn dưới 100% ngay từ thiết kế.

Thương hiệu tính tiền theo từng workspace
-----------------------------------------
`plan` nằm trên **workspace**, và checkout cũng scope theo workspace. Nghĩa là
mỗi thương hiệu là một workspace và **trả gói riêng** — đó chính là đòn bẩy mở
rộng doanh thu, và nó đã có sẵn về mặt cơ chế.

Vì vậy ở đây **không có trần số thương hiệu**: tạo thương hiệu thứ hai là mở một
thuê bao thứ hai, không phải lấn vào hạn mức của thuê bao thứ nhất. Bảng giá phải
nói thẳng điều này — bản trước bán "Chuỗi Doanh Nghiệp 799.000đ · nhiều thương
hiệu", đọc như một giá bao gồm nhiều thương hiệu, trong khi hệ thống tính từng
cái. Khách mua rồi thêm thương hiệu thứ hai sẽ phát hiện ra sự thật đúng lúc tệ
nhất.

Cái gói cao hơn thật sự mua thêm là **tầng tổ chức**: gom các workspace của cùng
một doanh nghiệp lại, mời người một lần cho cả tổ chức, và nhìn chéo sức khoẻ mọi
kênh. Đó là giá trị theo chiều ngang, không phải một hạn mức.

Số ở đây chưa được kiểm chứng
-----------------------------
Chúng dựng từ hình dung về quy mô một resort, một chuỗi cà phê, một spa có nhân
viên marketing — **không** từ dữ liệu khách thật, vì chưa có khách thật. Đây là
chỗ duy nhất cần sửa khi có số thật; đừng rải giới hạn ra từng service.
"""

from dataclasses import dataclass

from core.enums import Plan

#: Không giới hạn. Dùng số thay vì `None` để mọi so sánh viết một kiểu duy nhất —
#: `if used >= limit` đúng với cả trường hợp mở, không cần nhánh riêng.
UNLIMITED = 1_000_000


@dataclass(frozen=True)
class PlanLimits:
    """Trần của một gói. `label` là câu hiện cho người dùng khi họ đụng trần."""

    max_seats: int
    max_channels: int
    #: Số thương hiệu gói này **hướng tới** — dùng cho câu chữ ở bảng giá, không
    #: phải một trần được cưỡng chế. Xem docstring module: mỗi thương hiệu là một
    #: workspace và trả gói riêng, nên không có trần nào để chặn.
    intended_brands: int
    label: str


LIMITS: dict[Plan, PlanLimits] = {
    # Dùng thử: đủ để chạy hết một vòng vận hành thật (chủ + một nhân viên trực),
    # không đủ để một đội dùng miễn phí mãi.
    Plan.TRIAL: PlanLimits(max_seats=2, max_channels=2, intended_brands=1, label="Gói Trải Nghiệm"),
    # Một thương hiệu, một người vận hành chính kèm một người trực.
    Plan.TIEM_NHO: PlanLimits(
        max_seats=3, max_channels=3, intended_brands=1, label="Gói Khởi Nghiệp"
    ),
    # Đội nhiều người: có người soạn, người duyệt, vài người trực ca.
    Plan.TOAN_DIEN: PlanLimits(
        max_seats=10, max_channels=8, intended_brands=3, label="Gói Chuyên Nghiệp"
    ),
    # Chuỗi: nhiều chi nhánh, mỗi chi nhánh vài người trực.
    Plan.DOANH_NGHIEP: PlanLimits(
        max_seats=50, max_channels=UNLIMITED, intended_brands=20, label="Chuỗi Doanh Nghiệp"
    ),
}


def limits_for(plan: Plan) -> PlanLimits:
    """Trần của một gói. Gói lạ rơi về trần thấp nhất.

    Rơi xuống thấp nhất chứ không mở hết: một giá trị `plan` không đọc được (dòng
    dữ liệu cũ, sửa tay) mà mở toàn quyền là một lỗ hổng thương mại im lặng.
    """
    return LIMITS.get(plan, LIMITS[Plan.TRIAL])


class PlanLimitExceeded(Exception):
    """Đụng trần gói.

    Mang theo đủ dữ liệu để router dựng được một câu có ích — *"Gói Khởi Nghiệp
    cho 3 người, workspace này đã có 3"* — thay vì một chữ "vượt giới hạn" rồi để
    người dùng tự đoán phải làm gì.
    """

    def __init__(self, *, plan: Plan, resource: str, used: int, limit: int) -> None:
        limits = limits_for(plan)
        super().__init__(
            f"{limits.label} cho tối đa {limit} {resource}, hiện đã dùng {used}. "
            f"Nâng gói để thêm."
        )
        self.plan = plan
        self.resource = resource
        self.used = used
        self.limit = limit


def effective_limits(
    *, plan: Plan, extra_seats: int = 0, extra_channels: int = 0
) -> PlanLimits:
    """Trần **hiệu dụng**: trần gói cộng phần đã mua thêm.

    Mọi chỗ kiểm quyền phải dùng hàm này, không dùng `limits_for` trực tiếp — nếu
    không thì khách trả tiền cho ghế thứ tư vẫn bị chặn ở ghế thứ tư, và đó là lỗi
    tệ nhất trong nhóm này: thu tiền rồi không cấp.

    `UNLIMITED` cộng thêm vẫn là `UNLIMITED` về mặt thực tế; không cần nhánh riêng
    vì con số đã lớn hơn mọi quy mô thật.
    """
    base = limits_for(plan)
    return PlanLimits(
        max_seats=base.max_seats + max(0, extra_seats),
        max_channels=base.max_channels + max(0, extra_channels),
        intended_brands=base.intended_brands,
        label=base.label,
    )


def check_seats(
    *, plan: Plan, current: int, extra_seats: int = 0
) -> None:
    """Gọi **trước** khi thêm thành viên. `current` là số thành viên đang có."""
    limit = effective_limits(plan=plan, extra_seats=extra_seats).max_seats
    if current >= limit:
        raise PlanLimitExceeded(plan=plan, resource="người dùng", used=current, limit=limit)


def check_channels(
    *, plan: Plan, current: int, extra_channels: int = 0
) -> None:
    """Gọi **trước** khi nối kênh mới. `current` là số kênh đã nối."""
    limit = effective_limits(plan=plan, extra_channels=extra_channels).max_channels
    if current >= limit:
        raise PlanLimitExceeded(plan=plan, resource="kênh", used=current, limit=limit)
