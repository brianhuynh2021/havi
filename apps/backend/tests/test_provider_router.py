"""Test ProviderRouter — 3 lý do fallback ở SYSTEM_ARCHITECTURE.md §5.1.

Không cần DB hay network: dùng FakeProvider, kiểm đúng logic điều phối.
"""

import json

import pytest

from adapters.llm.fake import FakeProvider
from domain.policies.provider_router import (
    AllProvidersFailed,
    OutputValidationError,
    ProviderRouter,
)
from domain.ports.llm import (
    LLMPermanentError,
    LLMProvider,
    LLMRequest,
    LLMTransientError,
)

REQUEST = LLMRequest(
    system_prompt="Bạn là Havi.",
    user_prompt="Viết bài về gội đầu thảo dược.",
    output_schema={"type": "object"},
)


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise OutputValidationError(f"không phải JSON: {exc}") from exc


async def test_provider_dau_tien_ok_thi_khong_goi_provider_sau():
    gemini = FakeProvider(provider=LLMProvider.GEMINI, response_text='{"ok": true}')
    anthropic = FakeProvider(provider=LLMProvider.ANTHROPIC, response_text='{"ok": false}')
    router = ProviderRouter({LLMProvider.GEMINI: gemini, LLMProvider.ANTHROPIC: anthropic})

    result = await router.generate(REQUEST, validate=_parse_json)

    assert result.value == {"ok": True}
    assert result.served_by == LLMProvider.GEMINI
    assert len(anthropic.calls) == 0, "provider sau không được gọi khi provider đầu đã ok"


async def test_loi_transient_thi_chuyen_provider_ke_tiep():
    gemini = FakeProvider(
        provider=LLMProvider.GEMINI,
        error=LLMTransientError(LLMProvider.GEMINI, "HTTP 429 rate limit"),
    )
    anthropic = FakeProvider(provider=LLMProvider.ANTHROPIC, response_text='{"from": "anthropic"}')
    router = ProviderRouter({LLMProvider.GEMINI: gemini, LLMProvider.ANTHROPIC: anthropic})

    result = await router.generate(REQUEST, validate=_parse_json)

    assert result.served_by == LLMProvider.ANTHROPIC
    assert [a.failure_kind for a in result.attempts] == ["transient", None]


async def test_loi_permanent_cung_chuyen_provider_ke_tiep():
    """Sai key ở provider này không có nghĩa provider khác cũng sai key."""
    gemini = FakeProvider(
        provider=LLMProvider.GEMINI,
        error=LLMPermanentError(LLMProvider.GEMINI, "HTTP 401 invalid key"),
    )
    openai = FakeProvider(provider=LLMProvider.OPENAI, response_text='{"from": "openai"}')
    router = ProviderRouter({LLMProvider.GEMINI: gemini, LLMProvider.OPENAI: openai})

    result = await router.generate(REQUEST, validate=_parse_json)

    assert result.served_by == LLMProvider.OPENAI
    assert result.attempts[0].failure_kind == "permanent"


async def test_output_khong_hop_le_thi_thu_provider_khac_chu_khong_retry_cung_provider():
    """Retry cùng provider với cùng prompt hầu như ra cùng output lỗi — phải đổi provider."""
    gemini = FakeProvider(provider=LLMProvider.GEMINI, response_text="đây không phải JSON")
    anthropic = FakeProvider(provider=LLMProvider.ANTHROPIC, response_text='{"ok": true}')
    router = ProviderRouter({LLMProvider.GEMINI: gemini, LLMProvider.ANTHROPIC: anthropic})

    result = await router.generate(REQUEST, validate=_parse_json)

    assert result.served_by == LLMProvider.ANTHROPIC
    assert result.attempts[0].failure_kind == "invalid_output"
    assert len(gemini.calls) == 1, "không được gọi lại chính provider đã cho output lỗi"


async def test_provider_thieu_api_key_bi_bo_qua_khong_goi():
    gemini = FakeProvider(provider=LLMProvider.GEMINI, configured=False)
    anthropic = FakeProvider(provider=LLMProvider.ANTHROPIC, response_text='{"ok": true}')
    router = ProviderRouter({LLMProvider.GEMINI: gemini, LLMProvider.ANTHROPIC: anthropic})

    result = await router.generate(REQUEST, validate=_parse_json)

    assert result.served_by == LLMProvider.ANTHROPIC
    assert len(gemini.calls) == 0
    assert len(result.attempts) == 1, "provider chưa cấu hình không tính là một lần thử"


async def test_moi_provider_that_bai_thi_nem_loi_kem_lich_su_thu():
    router = ProviderRouter(
        {
            LLMProvider.GEMINI: FakeProvider(
                provider=LLMProvider.GEMINI,
                error=LLMTransientError(LLMProvider.GEMINI, "429"),
            ),
            LLMProvider.ANTHROPIC: FakeProvider(
                provider=LLMProvider.ANTHROPIC, response_text="không phải JSON"
            ),
        }
    )

    with pytest.raises(AllProvidersFailed) as exc_info:
        await router.generate(REQUEST, validate=_parse_json)

    kinds = [a.failure_kind for a in exc_info.value.attempts]
    assert kinds == ["transient", "invalid_output"]


async def test_khong_co_provider_nao_duoc_cau_hinh_thi_that_bai_ngay():
    router = ProviderRouter(
        {LLMProvider.GEMINI: FakeProvider(provider=LLMProvider.GEMINI, configured=False)}
    )
    with pytest.raises(AllProvidersFailed):
        await router.generate(REQUEST, validate=_parse_json)


async def test_token_duoc_cong_don_qua_moi_lan_thu():
    """Provider lỗi output vẫn tốn token — cost phải tính cả lần thử thất bại."""
    router = ProviderRouter(
        {
            LLMProvider.GEMINI: FakeProvider(
                provider=LLMProvider.GEMINI,
                response_text="không phải JSON",
                tokens_in=10,
                tokens_out=20,
            ),
            LLMProvider.ANTHROPIC: FakeProvider(
                provider=LLMProvider.ANTHROPIC,
                response_text='{"ok": true}',
                tokens_in=30,
                tokens_out=40,
            ),
        }
    )

    result = await router.generate(REQUEST, validate=_parse_json)

    assert result.total_tokens_in == 40
    assert result.total_tokens_out == 60
    assert result.response.tokens_in == 30, "response chỉ mang token của lần thành công"


async def test_thu_tu_uu_tien_doi_duoc_cho_cost_routing():
    """Gói giá khác nhau map sang thứ tự khác nhau — router không cần biết pricing."""
    gemini = FakeProvider(provider=LLMProvider.GEMINI, response_text='{"who": "gemini"}')
    openai = FakeProvider(provider=LLMProvider.OPENAI, response_text='{"who": "openai"}')
    router = ProviderRouter({LLMProvider.GEMINI: gemini, LLMProvider.OPENAI: openai})

    result = await router.generate(
        REQUEST, validate=_parse_json, order=(LLMProvider.OPENAI, LLMProvider.GEMINI)
    )

    assert result.value == {"who": "openai"}
    assert len(gemini.calls) == 0
