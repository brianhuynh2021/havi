"""Schema và validation cho output của Content Engine.

Đây là nơi enforce nguyên tắc #5 (ROADMAP.md §1): một lần gọi LLM sinh nhiều bản
theo kênh. Và nơi chặn banned claims trước khi draft đến tay chủ tiệm — không tin
model tự nhớ danh sách từ cấm trong prompt.
"""

import json
import unicodedata

from pydantic import BaseModel, Field, ValidationError

from core.enums import Channel
from domain.policies.provider_router import OutputValidationError

MIN_DRAFTS = 1
MAX_DRAFTS = 6


class GeneratedDraft(BaseModel):
    channel: Channel
    kind: str = Field(min_length=1, max_length=60)
    text: str = Field(min_length=1, max_length=4000)
    media_note: str | None = Field(default=None, max_length=500)


class GeneratedDrafts(BaseModel):
    drafts: list[GeneratedDraft] = Field(min_length=MIN_DRAFTS, max_length=MAX_DRAFTS)


def output_json_schema() -> dict:
    """JSON Schema gửi cho provider để nó trả đúng shape ngay từ đầu."""
    return {
        "type": "object",
        "properties": {
            "drafts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "enum": [c.value for c in Channel],
                        },
                        "kind": {"type": "string"},
                        "text": {"type": "string"},
                        "media_note": {"type": "string"},
                    },
                    "required": ["channel", "kind", "text"],
                },
            }
        },
        "required": ["drafts"],
    }


def _normalize(text: str) -> str:
    """Bỏ dấu + lowercase để so khớp banned claim không lệ thuộc cách viết.

    "Cam Kết 100%" và "cam ket 100%" phải cùng bị chặn — model có thể viết hoa
    hoặc user gõ từ cấm không dấu khi cấu hình brand profile.
    """
    lowered = text.lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def find_banned_claims(text: str, banned_claims: list[str]) -> list[str]:
    haystack = _normalize(text)
    return [claim for claim in banned_claims if claim.strip() and _normalize(claim) in haystack]


def parse_and_validate(
    raw_text: str, *, banned_claims: list[str]
) -> GeneratedDrafts:
    """Parse JSON → validate schema → chặn banned claims.

    Ném `OutputValidationError` để `ProviderRouter` hiểu là nên thử provider khác
    (retry cùng provider với cùng prompt hầu như ra cùng lỗi).
    """
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise OutputValidationError(f"output không phải JSON hợp lệ: {exc}") from exc

    try:
        drafts = GeneratedDrafts.model_validate(payload)
    except ValidationError as exc:
        raise OutputValidationError(f"output sai schema: {exc.error_count()} lỗi") from exc

    if banned_claims:
        for index, draft in enumerate(drafts.drafts):
            found = find_banned_claims(draft.text, banned_claims)
            if found:
                raise OutputValidationError(
                    f"draft #{index + 1} ({draft.channel}) chứa claim bị cấm: {found}"
                )

    return drafts
