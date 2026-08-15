"""Mock provider cho local dev — sinh draft hợp lệ mà không gọi API tính tiền.

Khác `FakeProvider` ở `fake.py`: cái đó là test double, mỗi test tự nhét sẵn
chuỗi output nó muốn. Cái này tự chế bài từ chính prompt nhận được, để chạy tay
ở local ra nội dung đọc được như thật — bấm "Để Havi viết cho chị" mười lần
cũng không tốn đồng nào.

Không dùng ở staging/production: ở đó phải gọi model thật mới biết prompt và
schema có thực sự ổn không (xem `build_provider_router`).
"""

import json
import re

from domain.ports.llm import (
    LLMProvider,
    LLMProviderPort,
    LLMRequest,
    LLMResponse,
)

# Ba kênh pilot, khớp `DEFAULT_CHANNELS` mà prompt yêu cầu. Mỗi kênh một giọng
# riêng — Facebook kể chuyện, Zalo nhắn trực tiếp, Google Business trang trọng —
# để lúc xem trên UI còn phân biệt được kênh nào ra kênh nào.
_TEMPLATES: list[tuple[str, str, str]] = [
    (
        "facebook_page",
        "Bài ảnh",
        "Chào cả nhà, {tiem} có tin vui nè! {noi_dung} "
        "Tiệm làm cẩn thận từng bước nên chị em cứ yên tâm nha. "
        "Chị nào quan tâm thì nhắn tiệm để được tư vấn thêm ạ!",
    ),
    (
        "zalo_oa",
        "Tin Zalo",
        "Chào chị, {tiem} gửi chị thông tin ạ: {noi_dung} "
        "Chị nhắn lại tin này để em sắp lịch giúp chị nhé!",
    ),
    (
        "google_business",
        "Cập nhật Google",
        "{tiem} thông báo: {noi_dung} "
        "Quý khách vui lòng liên hệ trước để được phục vụ chu đáo nhất.",
    ),
]

_SHOP_FALLBACK = "Tiệm"


def _extract(pattern: str, text: str, fallback: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def _join_raw_inputs(user_prompt: str) -> str:
    """Gom liệu thô từ khối "Liệu thô chủ tiệm vừa nạp:" trong user prompt.

    Bám đúng cấu trúc `build_user_prompt` dựng ra: mỗi dòng dạng
    `- <nhãn>: <text>`, và khối kết thúc ở dòng trống. Ảnh/ghi âm không có text
    nên bị bỏ qua — mock chỉ kể lại được phần chữ.
    """
    lines = user_prompt.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith("Liệu thô"))
    except StopIteration:
        return ""

    parts: list[str] = []
    for line in lines[start + 1 :]:
        if not line.strip():
            break
        if ":" in line:
            text = line.split(":", 1)[1].strip()
            if text:
                parts.append(text)

    joined = " ".join(parts).strip()
    if joined and not joined.endswith((".", "!", "?")):
        joined += "."
    return joined


class MockProvider(LLMProviderPort):
    """Trả draft dựng từ prompt. Luôn `is_configured` — không cần API key."""

    @property
    def provider(self) -> LLMProvider:
        # Mượn danh Gemini để router chọn nó đầu tiên theo thứ tự mặc định.
        return LLMProvider.GEMINI

    @property
    def is_configured(self) -> bool:
        return True

    async def generate(self, request: LLMRequest) -> LLMResponse:
        # Liệu thô của user nằm trong user_prompt; tên tiệm nằm trong system
        # prompt do brand profile dựng ra. Lấy được thì bài đọc tự nhiên hơn
        # hẳn, lấy không được cũng không sao vì đây chỉ là dữ liệu để nhìn.
        tiem = _extract(r"^Tên tiệm:\s*(.+)$", request.user_prompt, _SHOP_FALLBACK)
        # Chỉ nạp ảnh thì không có chữ nào để kể lại — mock không "xem" được ảnh.
        noi_dung = _join_raw_inputs(request.user_prompt) or (
            "tiệm vừa có dịch vụ mới, mời chị ghé trải nghiệm."
        )

        templates = [
            (channel, kind, template)
            for channel, kind, template in _TEMPLATES
            if (
                channel in request.user_prompt
                or channel.replace("_", " ") in request.user_prompt.lower()
            )
        ]
        if not templates:
            templates = _TEMPLATES

        drafts = [
            {
                "channel": channel,
                "kind": kind,
                "text": template.format(tiem=tiem, noi_dung=noi_dung),
            }
            for channel, kind, template in templates
        ]
        text = json.dumps({"drafts": drafts}, ensure_ascii=False)

        # Token đếm thô theo độ dài — event log vẫn có số để nhìn, nhưng đây
        # KHÔNG phải cost thật và không được dùng để tính margin.
        return LLMResponse(
            text=text,
            provider=self.provider,
            model="mock-local",
            tokens_in=len(request.system_prompt + request.user_prompt) // 4,
            tokens_out=len(text) // 4,
            latency_ms=1,
        )
