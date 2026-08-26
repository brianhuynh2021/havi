"""Phân loại việc và thứ tự hàng đợi.

Không test "câu này ra đúng nhóm này" cho từng câu — bộ keyword còn sửa nhiều.
Test ở đây khoá **luật**: cái gì phải nổi lên trước cái gì, và cái gì không được
biến mất khỏi hàng đợi.
"""

from domain.policies.inbox_triage import (
    TicketCategory,
    classify,
    is_costly,
    priority_of,
)
from domain.policies.work_queue import Priority, WorkKind, priority_for


class TestClassify:
    def test_khach_hoi_gia_vao_nhom_price(self):
        assert classify("Cho em xin bảng giá gói mặt với ạ") is TicketCategory.PRICE
        assert classify("dịch vụ này bao nhiêu tiền vậy shop") is TicketCategory.PRICE

    def test_khong_dau_van_bat_duoc(self):
        """Khách gõ điện thoại thường không bỏ dấu. Bỏ qua chuyện này là mất
        khoảng một nửa số tin hỏi giá thật."""
        assert classify("gia bao nhieu a") is TicketCategory.PRICE
        assert classify("cho em dat lich chieu nay") is TicketCategory.BOOKING

    def test_dat_lich_vao_nhom_booking(self):
        assert classify("Em muốn đặt lịch tối mai còn chỗ không") is TicketCategory.BOOKING

    def test_khieu_nai_thang_hoi_gia_khi_tin_co_ca_hai(self):
        """Một tin vừa phàn nàn vừa hỏi giá tính là khiếu nại — đó là nửa cần xử
        lý cẩn thận hơn, và xử lý sai thì thành đánh giá một sao."""
        assert (
            classify("Lần trước làm tệ quá, giờ giá còn bao nhiêu mà đòi em quay lại")
            is TicketCategory.COMPLAINT
        )

    def test_hoi_thong_tin_vao_nhom_info(self):
        assert classify("Mấy giờ mở cửa vậy shop") is TicketCategory.INFO

    def test_KHONG_khop_bay_thanh_HONG(self):
        """Hồi quy: bản đầu khớp chuỗi con, nên `"hong"` bắt luôn `"khong"` — và
        gần như mọi câu tiếng Việt đều có chữ "không", nên mọi tin đều thành khiếu
        nại. Khớp theo biên từ mới đúng."""
        assert classify("Em muốn đặt lịch tối mai còn chỗ không") is TicketCategory.BOOKING
        assert classify("Không biết chỗ mình có làm cái này không") is not TicketCategory.COMPLAINT

    def test_tu_don_mo_ho_khong_keo_sai_nhom(self):
        """`"gia"` cũng là "gia đình"/"tham gia"; `"cham"` cũng là "chăm sóc";
        `"tien"` cũng là "tiện". Từ đơn mơ hồ đã bị loại khỏi bộ keyword."""
        assert classify("cả gia đình em muốn tham gia") is not TicketCategory.PRICE
        assert classify("bên mình có chăm sóc da không") is not TicketCategory.COMPLAINT
        assert classify("chỗ mình có tiện đường không") is not TicketCategory.PRICE

    def test_khong_khop_thi_other_chu_khong_doan(self):
        assert classify("ok") is TicketCategory.OTHER
        assert classify("👍") is TicketCategory.OTHER


class TestPriority:
    def test_khieu_nai_tren_hoi_gia_tren_hoi_thong_tin(self):
        """Hỏi giá chậm thì mất một đơn; khiếu nại bị bỏ mặc thì mất nhiều đơn."""
        assert priority_of("complaint") < priority_of("price")
        assert priority_of("price") < priority_of("info")
        assert priority_of("info") < priority_of("other")

    def test_category_thieu_hoac_la_khong_lam_sap_ma_roi_xuong_cuoi(self):
        """Dòng ghi trước khi có cột `category`, hoặc giá trị sửa tay, vẫn phải
        nằm trong hàng đợi — chỉ là ở cuối. Không việc nào được biến mất."""
        assert priority_of(None) == priority_of("other")
        assert priority_of("nhom_khong_ton_tai") == priority_of("other")

    def test_nhom_ton_tien_duoc_danh_dau_rieng(self):
        """Báo cáo "bỏ sót" đếm riêng nhóm này: sót 12 tin hỏi giá là một câu bán
        hàng, sót 12 tin hỏi giờ mở cửa thì không."""
        assert is_costly("price") is True
        assert is_costly("booking") is True
        assert is_costly("complaint") is True
        assert is_costly("info") is False
        assert is_costly(None) is False


class TestWorkQueueOrder:
    def test_kenh_chet_len_dau_tien(self):
        """Kênh mất quyền thì mọi việc khác vô nghĩa: không đăng được, không nhận
        được tin mới, và số liệu trên màn hình đang nói dối về hiện trạng."""
        assert priority_for(kind=WorkKind.CONNECTION) == Priority.BLOCKING
        assert priority_for(kind=WorkKind.CONNECTION) < priority_for(
            kind=WorkKind.INBOX, category="complaint"
        )

    def test_nhap_cho_duyet_xuong_duoi_moi_viec_co_khach_dang_doi(self):
        """Nháp chờ duyệt là việc bị chặn, nhưng chưa mất gì — nội dung vẫn nằm
        đó. Mọi thứ có khách đang đợi đều xếp trên nó."""
        approval = priority_for(kind=WorkKind.APPROVAL)
        for category in ("complaint", "price", "booking", "info"):
            assert priority_for(kind=WorkKind.INBOX, category=category) < approval

    def test_bai_dang_loi_tren_hoi_thong_tin(self):
        """Bài không lên được kênh là mất âm thầm — không ai phàn nàn, nên nếu
        không đẩy lên trước việc thường thì không bao giờ có ai xử lý."""
        assert priority_for(kind=WorkKind.PUBLISH_FAILURE) < priority_for(
            kind=WorkKind.INBOX, category="info"
        )

    def test_hoi_gia_tren_bai_dang_loi(self):
        """Khách đang đợi trả lời thắng một bài đăng lại được."""
        assert priority_for(kind=WorkKind.INBOX, category="price") < priority_for(
            kind=WorkKind.PUBLISH_FAILURE
        )
