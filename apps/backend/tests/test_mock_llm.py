"""Mock LLM cho local dev — và chốt chặn không cho nó lọt ra staging/production."""

import pytest
from pydantic import ValidationError

from adapters.llm.mock import MockProvider
from core.config import Settings
from domain.policies.content_output import parse_and_validate
from domain.ports.llm import LLMRequest


def _user_prompt(*raw: str, shop: str = "Spa An Nhiên") -> str:
    """Dựng đúng shape `build_user_prompt` sinh ra — mock bám vào shape này."""
    lines = [f"Tên tiệm: {shop}", "", "Liệu thô chủ tiệm vừa nạp:"]
    lines += [f"- Ghi chú chủ tiệm gõ: {r}" for r in raw]
    lines += ["", "Viết nội dung cho các kênh sau:"]
    return "\n".join(lines)


def _request(user_prompt: str | None = None) -> LLMRequest:
    return LLMRequest(
        system_prompt="Bạn là Havi — nhân viên marketing của một spa ở Việt Nam.",
        user_prompt=user_prompt or _user_prompt("Giảm 20% gói gội đầu thảo dược"),
        output_schema={},
    )


async def test_mock_tra_output_dung_schema():
    """Nếu mock trả sai shape thì local chạy được mà production thì vỡ."""
    response = await MockProvider().generate(_request())

    drafts = parse_and_validate(response.text, banned_claims=[])
    assert len(drafts.drafts) == 5
    assert {d.channel.value for d in drafts.drafts} == {
        "facebook_page",
        "youtube",
        "tiktok",
        "reels",
        "google_business",
    }
    assert all(d.text.strip() for d in drafts.drafts)


async def test_mock_dua_lieu_tho_va_ten_tiem_vao_bai():
    """Bài phải bám liệu thô, không phải văn mẫu cố định — nhìn UI mới có nghĩa."""
    response = await MockProvider().generate(
        _request(_user_prompt("Khai trương chi nhánh 2 tại Quận 7"))
    )

    assert "Khai trương chi nhánh 2 tại Quận 7" in response.text
    assert "Spa An Nhiên" in response.text
    # Không được lấy nhầm chữ trong system prompt làm tên tiệm.
    assert "làm đẹp ở Việt Nam" not in response.text


async def test_mock_gom_nhieu_lieu_tho():
    response = await MockProvider().generate(
        _request(_user_prompt("Giảm 20% gói gội đầu", "Còn đúng 30 suất"))
    )
    assert "Giảm 20% gói gội đầu" in response.text
    assert "Còn đúng 30 suất" in response.text


async def test_mock_chi_nap_anh_van_ra_bai_doc_duoc():
    """Ảnh không có text — mock không "xem" được ảnh, phải có câu thay thế."""
    prompt = "\n".join(
        [
            "Tên tiệm: Spa An Nhiên",
            "",
            "Liệu thô chủ tiệm vừa nạp:",
            "- Ảnh chủ tiệm vừa gửi",
            "",
            "Viết nội dung cho các kênh sau:",
        ]
    )
    response = await MockProvider().generate(_request(prompt))

    drafts = parse_and_validate(response.text, banned_claims=[])
    assert len(drafts.drafts) == 5
    assert all(len(d.text) > 40 for d in drafts.drafts)


async def test_mock_khong_can_api_key():
    assert MockProvider().is_configured is True


async def test_mock_ghi_ro_model_de_khong_nham_voi_that():
    """`model` phải nói rõ là mock — event log là chỗ duy nhất truy lại sau này."""
    response = await MockProvider().generate(_request())
    assert response.model == "mock-local"


def test_bat_mock_o_staging_thi_khong_khoi_dong_duoc():
    """Draft văn mẫu mà tưởng AI viết rồi đăng lên Facebook thật là lỗi không sửa được.

    Chặn ngay lúc khởi động, không phải phát hiện sau khi bài đã lên mạng.
    """
    with pytest.raises(ValidationError, match="không được phép khi HAVI_ENV"):
        Settings(env="staging", use_mock_llm=True)

    with pytest.raises(ValidationError, match="không được phép khi HAVI_ENV"):
        Settings(env="production", use_mock_llm=True)


def test_local_van_bat_mock_duoc():
    assert Settings(env="local", use_mock_llm=True).use_mock_llm is True


def test_staging_tat_mock_thi_khoi_dong_binh_thuong():
    """Staging thật phải tắt các cấu hình local-only — đây là config đúng.

    `disable_rate_limit=False` khai tường minh: conftest set
    `HAVI_DISABLE_RATE_LIMIT=true` cho cả suite, và Settings đọc env nên không
    khai ở đây thì chính validator mới sẽ (đúng) chặn config staging này.
    """
    settings = Settings(
        env="staging",
        use_mock_llm=False,
        use_fake_publisher=False,
        disable_rate_limit=False,
        email_provider="smtp",
        email_from="no-reply@havi.vn",
        smtp_host="smtp.havi.vn",
    )
    assert settings.use_mock_llm is False
    assert settings.use_fake_publisher is False
    assert settings.disable_rate_limit is False
    assert settings.email_provider == "smtp"


def test_tat_rate_limit_o_staging_thi_khong_khoi_dong_duoc():
    """Sai kiểu im lặng nhất trong ba cờ: không có gì hiện ra, app chạy y như
    thường, chỉ là brute force mật khẩu không còn bị chặn và một script lỗi đốt
    hết quota LLM trong vài phút."""
    for env in ("staging", "production"):
        with pytest.raises(ValidationError, match="không được phép khi HAVI_ENV"):
            Settings(
                env=env,
                use_mock_llm=False,
                use_fake_publisher=False,
                disable_rate_limit=True,
            )


def test_bat_fake_publisher_o_staging_thi_khong_khoi_dong_duoc():
    """Sai kiểu này im lặng và tệ hơn mock LLM.

    Mọi bài đều báo "đã đăng", dashboard xanh, chủ tiệm tin là Facebook đã có
    bài — trong khi Trang trống trơn. Phát hiện ra thì đã mất mấy ngày nội dung.
    """
    with pytest.raises(ValidationError, match="không được phép khi HAVI_ENV"):
        Settings(env="staging", use_mock_llm=False, use_fake_publisher=True)

    with pytest.raises(ValidationError, match="không được phép khi HAVI_ENV"):
        Settings(env="production", use_mock_llm=False, use_fake_publisher=True)


def test_local_van_bat_fake_publisher_duoc():
    assert Settings(env="local", use_fake_publisher=True).use_fake_publisher is True
