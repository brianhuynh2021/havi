"""Cảnh báo phải nói đúng chỗ Facebook hiện khác chữ đã gửi."""

from domain.policies.facebook_render import (
    FACEBOOK_TRUNCATE_CHARS,
    facebook_render_warnings,
)


def _codes(text: str) -> set[str]:
    return {warning.code for warning in facebook_render_warnings(text)}


def test_bai_ngan_thuan_chu_khong_co_canh_bao_nao():
    text = "Cuối tuần này tiệm giảm 20% gội đầu thảo dược. Nhắn tin để giữ chỗ nha chị."
    assert facebook_render_warnings(text) == []


def test_bai_dai_hon_nguong_bao_bi_cat_va_noi_ro_cat_o_dau():
    text = "a" * (FACEBOOK_TRUNCATE_CHARS + 250)
    warnings = facebook_render_warnings(text)

    assert [w.code for w in warnings] == ["TRUNCATED"]
    assert warnings[0].at_char == FACEBOOK_TRUNCATE_CHARS, (
        "giao diện cần biết cắt ở ký tự nào để vẽ ranh giới, không phải tự đoán lại"
    )
    assert "250" in warnings[0].message


def test_dung_nguong_thi_chua_canh_bao():
    """Ranh giới là "hơn", không phải "bằng" — bài vừa đủ vẫn hiện trọn."""
    assert facebook_render_warnings("a" * FACEBOOK_TRUNCATE_CHARS) == []


def test_markdown_dam_bi_bao_vi_facebook_hien_nguyen_dau_sao():
    warnings = facebook_render_warnings("**1. MIT dạy tư duy tối ưu**")
    assert [w.code for w in warnings] == ["MARKDOWN_NOT_SUPPORTED"]
    assert "**chữ đậm**" in warnings[0].message


def test_gach_dau_dong_bang_dau_sao_khong_bi_bao_lam():
    """"* Bắt chép đúng từng bước" là gạch đầu dòng người đọc vẫn hiểu.

    Bắt nó thành `*nghiêng*` sẽ khiến cảnh báo kêu ở mọi bài có bullet — và một
    cảnh báo kêu ở mọi bài thì người dùng học cách bỏ qua nó.
    """
    text = "Thực trạng:\n* Bắt chép đúng từng bước\n* Slide cả chục năm không đổi"
    assert facebook_render_warnings(text) == []


def test_cac_dang_markdown_khac_deu_bi_bat():
    assert "MARKDOWN_NOT_SUPPORTED" in _codes("*chữ nghiêng* trong bài")
    assert "MARKDOWN_NOT_SUPPORTED" in _codes("_gạch dưới_ ở đây")
    assert "MARKDOWN_NOT_SUPPORTED" in _codes("# Tiêu đề bài viết")
    assert "MARKDOWN_NOT_SUPPORTED" in _codes("xem [trang này](https://havi.vn)")


def test_gach_duoi_giua_ten_bien_khong_bi_bat():
    """`content_item_versions` là một chữ, không phải chữ gạch dưới."""
    assert facebook_render_warnings("bảng content_item_versions lưu lịch sử") == []


def test_nhieu_hashtag_bi_bao_la_trong_nhu_spam():
    text = "Gội đầu #spa #thugian #goidau #duongsinh #thaomoc #uudai #saigon #quan1"
    warnings = facebook_render_warnings(text)
    assert [w.code for w in warnings] == ["MANY_HASHTAGS"]
    assert "8" in warnings[0].message


def test_it_hashtag_thi_khong_sao():
    assert facebook_render_warnings("Gội đầu thảo dược #spa #uudai") == []


def test_bai_linkedin_dan_vao_bao_du_ca_hai_van_de():
    """Đúng ca đã dẫn tới việc viết file này: bài dài, có Markdown."""
    text = (
        "Học IT ở đại học và thực tế đi làm.\n\n"
        "**1. MIT dạy tư duy tối ưu ngay từ dòng code đầu tiên**\n"
        + "Nội dung dài. " * 80
    )
    codes = _codes(text)
    assert codes == {"TRUNCATED", "MARKDOWN_NOT_SUPPORTED"}
