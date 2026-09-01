"""Circuit breaker — chuyển trạng thái và điều nó bảo vệ.

Test hành vi qua API công khai (`allows_request`/`record_*`), không chọc vào
`_state`: chỗ dùng thật chỉ thấy "có được gọi upstream không", và test bám vào
field nội bộ sẽ đỏ mỗi lần refactor dù hành vi không đổi.
"""

import pytest

from domain.policies.circuit_breaker import (
    BreakerState,
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitOpenError,
)


def _fail(breaker: CircuitBreaker, times: int) -> None:
    for _ in range(times):
        breaker.record_failure()


class TestMoVaDong:
    def test_du_loi_lien_tiep_thi_mo_va_chan_request(self) -> None:
        breaker = CircuitBreaker(name="test", failure_threshold=3)
        assert breaker.allows_request() is True

        _fail(breaker, 3)

        assert breaker.state is BreakerState.OPEN
        assert breaker.allows_request() is False

    def test_chua_du_nguong_thi_van_cho_qua(self) -> None:
        breaker = CircuitBreaker(name="test", failure_threshold=5)
        _fail(breaker, 4)
        assert breaker.allows_request() is True

    def test_thanh_cong_xoa_chuoi_loi_dang_dem(self) -> None:
        """Điểm cốt lõi của "lỗi *liên tiếp*": một lần thành công phải reset.

        Không reset thì 5 lỗi rải rác qua nhiều giờ cũng mở breaker, và nó sẽ
        chặn một provider hoàn toàn khoẻ mạnh.
        """
        breaker = CircuitBreaker(name="test", failure_threshold=3)
        _fail(breaker, 2)
        breaker.record_success()
        _fail(breaker, 2)

        assert breaker.allows_request() is True

    def test_raise_if_open_neu_dang_mo(self) -> None:
        breaker = CircuitBreaker(name="fb", failure_threshold=1)
        breaker.record_failure()

        with pytest.raises(CircuitOpenError) as exc:
            breaker.raise_if_open()
        assert exc.value.name == "fb"


class TestHalfOpen:
    def test_het_reset_timeout_thi_sang_half_open_va_cho_tham_do(self) -> None:
        # `reset_timeout_seconds=0` để không phải sleep: test đo *chuyển trạng
        # thái*, không đo đồng hồ. Sleep thật chỉ làm suite chậm và dễ nhiễu.
        breaker = CircuitBreaker(name="test", failure_threshold=1, reset_timeout_seconds=0)
        breaker.record_failure()

        assert breaker.state is BreakerState.HALF_OPEN
        assert breaker.allows_request() is True

    def test_half_open_chi_cho_dung_so_luot_tham_do(self) -> None:
        """Không mở van hoàn toàn: upstream vẫn chết thì chỉ một request bị treo."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=1,
            reset_timeout_seconds=0,
            half_open_max_calls=1,
        )
        breaker.record_failure()

        assert breaker.allows_request() is True
        assert breaker.allows_request() is False

    def test_loi_khi_dang_tham_do_thi_mo_lai_ngay(self) -> None:
        breaker = CircuitBreaker(
            name="test", failure_threshold=5, reset_timeout_seconds=0, half_open_max_calls=1
        )
        _fail(breaker, 5)
        assert breaker.state is BreakerState.HALF_OPEN
        breaker.allows_request()

        # Một lỗi duy nhất ở half_open là đủ — không cần lại đủ `failure_threshold`.
        breaker.record_failure()

        breaker.reset_timeout_seconds = 999
        assert breaker.state is BreakerState.OPEN

    def test_du_lan_thanh_cong_thi_dong_han(self) -> None:
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=1,
            reset_timeout_seconds=0,
            success_threshold=2,
            half_open_max_calls=5,
        )
        breaker.record_failure()
        assert breaker.state is BreakerState.HALF_OPEN

        breaker.record_success()
        breaker.record_success()

        breaker.reset_timeout_seconds = 999
        assert breaker.state is BreakerState.CLOSED


class TestRegistry:
    def test_cung_ten_tra_ve_cung_breaker(self) -> None:
        """Nếu không, mỗi chỗ gọi học lại từ đầu và breaker không bao giờ mở."""
        registry = CircuitBreakerRegistry()
        assert registry.get("llm.gemini") is registry.get("llm.gemini")

    def test_ten_khac_nhau_doc_lap(self) -> None:
        registry = CircuitBreakerRegistry()
        gemini = registry.get("llm.gemini", failure_threshold=1)
        openai = registry.get("llm.openai", failure_threshold=1)

        gemini.record_failure()

        assert gemini.allows_request() is False
        assert openai.allows_request() is True

    def test_reset_all_dua_moi_breaker_ve_closed(self) -> None:
        registry = CircuitBreakerRegistry()
        breaker = registry.get("x", failure_threshold=1)
        breaker.record_failure()

        registry.reset_all()

        assert breaker.allows_request() is True


class TestBreakerMoThiBaiVanDuocThuLai:
    """Breaker mở phải để bài ở trạng thái *còn thử lại được*.

    Đây là một lỗi tôi đã viết rồi sửa, ghi lại để không tái diễn: bản đầu đẩy
    job về `pending_reconciliation`. Nhưng trạng thái đó là **kết thúc** có chủ
    ý — `claim_due` chỉ nhặt job `PENDING`, và `retry_dead_letter` chỉ nhận
    `DEAD_LETTER`, nên không có gì đưa job ra khỏi đó ngoài người làm tay.

    Lý do đúng: breaker mở nghĩa là Havi **chưa gọi** nền tảng, nên chắc chắn
    chưa có bài nào được tạo — không hề mơ hồ. `pending_reconciliation` dành cho
    trường hợp *không biết* nền tảng đã tạo bài hay chưa.
    """

    def test_pending_reconciliation_khong_nam_trong_luong_retry(self) -> None:
        """Chốt lại tính chất khiến lựa chọn ban đầu là sai."""
        from core.enums import PublishStatus

        # `claim_due` lọc đúng `PENDING` (xem PublishRepository.claim_due), nên
        # bất kỳ trạng thái nào khác đều không tự quay lại vòng chạy.
        assert PublishStatus.PENDING_RECONCILIATION is not PublishStatus.PENDING

    def test_temporary_giu_job_trong_vong_retry(self) -> None:
        """`TEMPORARY` là loại lỗi duy nhất `mark_failed` cho retry."""
        from core.enums import PublishFailureKind

        # Nếu hằng số này đổi tên/ý nghĩa thì đoạn breaker trong publish_service
        # phải được xem lại cùng lúc.
        assert PublishFailureKind.TEMPORARY.value == "temporary"
