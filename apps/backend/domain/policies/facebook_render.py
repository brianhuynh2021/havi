"""Facebook hiện bài **không** giống hệt chữ ta gửi lên — cảnh báo trước chỗ lệch.

Vấn đề file này giải
--------------------
Người viết sẵn một bài ở nơi khác rồi dán vào Havi. Bài đó thường mang theo quy
ước của nơi nó được viết, và Facebook không hiểu quy ước nào cả:

- `**chữ đậm**` của Markdown lên Trang là **nguyên dấu sao**. Người viết thấy chữ
  đậm trong ô soạn của họ, khách thấy `**1. MIT dạy tư duy**`.
- Bài dài bị cắt sau khoảng 800 ký tự, phần còn lại nằm sau nút "Xem thêm". Một
  bài LinkedIn 2000 ký tự lên Trang là bị gãy ở giữa câu, và người đăng chỉ biết
  sau khi nó đã lên.

Cả hai đều không phải lỗi của bài viết, và cả hai đều **không thể phát hiện sau
khi đăng** — lúc đó nó đã ở trên tường khách. Nên chúng được nói ra ở đây, trước
khi đăng, kèm chỗ chính xác bị ảnh hưởng.

Đây là cảnh báo, không phải chặn
--------------------------------
Không có mục nào ở đây khiến bài không đăng được. Bài dài có thể là chủ ý; dấu
sao có thể là ký hiệu người viết muốn giữ. Quyền quyết định là của người đăng —
việc của Havi là để họ không bị *bất ngờ*.

Ngưỡng 800 là con số Facebook dùng để cắt, không phải giới hạn cứng; giới hạn
thật của một bài Trang lớn hơn nhiều lần và không đáng nhắc tới ở đây.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

#: Số ký tự Facebook hiện trước khi chèn "Xem thêm". Xấp xỉ — Facebook không
#: công bố con số chính xác và nó thay đổi theo thiết bị.
FACEBOOK_TRUNCATE_CHARS = 800

#: Trên bao nhiêu hashtag thì bài trông như spam. Facebook không phạt theo số
#: lượng, nhưng người đọc thì có.
HASHTAG_SOFT_LIMIT = 6

#: `**đậm**`, `*nghiêng*`, `_gạch dưới_`, `# tiêu đề`, `[chữ](link)`.
#:
#: `*` một dấu phải có chữ liền kề hai bên để không bắt dấu sao dùng làm gạch
#: đầu dòng ("* Bắt chép đúng từng bước") — đó là ký hiệu người đọc vẫn hiểu, còn
#: `*nghiêng*` thì không.
_MARKDOWN_PATTERNS = (
    (re.compile(r"\*\*[^*\n]+\*\*"), "**chữ đậm**"),
    (re.compile(r"(?<!\*)\*[^\s*][^*\n]*[^\s*]\*(?!\*)"), "*chữ nghiêng*"),
    (re.compile(r"(?<![\w_])_[^_\n]+_(?![\w_])"), "_gạch dưới_"),
    (re.compile(r"^#{1,6}\s+\S", re.MULTILINE), "# tiêu đề"),
    (re.compile(r"\[[^\]\n]+\]\([^)\n]+\)"), "[chữ](link)"),
)

_HASHTAG = re.compile(r"(?<!\w)#\w+")


@dataclass(frozen=True)
class RenderWarning:
    """Một chỗ bài sẽ hiện khác với điều người viết thấy khi soạn."""

    code: Literal["TRUNCATED", "MARKDOWN_NOT_SUPPORTED", "MANY_HASHTAGS"]
    message: str
    #: Ký tự thứ mấy Facebook cắt — chỉ có ở `TRUNCATED`, để giao diện vẽ được
    #: đúng chỗ ranh giới thay vì tự đoán lại.
    at_char: int | None = None


def facebook_render_warnings(text: str) -> list[RenderWarning]:
    """Những chỗ Facebook sẽ hiện khác chữ đã gửi. Rỗng nghĩa là hiện y nguyên."""
    warnings: list[RenderWarning] = []

    if len(text) > FACEBOOK_TRUNCATE_CHARS:
        hidden = len(text) - FACEBOOK_TRUNCATE_CHARS
        warnings.append(
            RenderWarning(
                code="TRUNCATED",
                message=(
                    f"Facebook chỉ hiện khoảng {FACEBOOK_TRUNCATE_CHARS} ký tự đầu; "
                    f"{hidden} ký tự còn lại nằm sau nút “Xem thêm”."
                ),
                at_char=FACEBOOK_TRUNCATE_CHARS,
            )
        )

    found = [label for pattern, label in _MARKDOWN_PATTERNS if pattern.search(text)]
    if found:
        warnings.append(
            RenderWarning(
                code="MARKDOWN_NOT_SUPPORTED",
                message=(
                    "Facebook không hiểu Markdown — "
                    f"{', '.join(found)} sẽ hiện nguyên ký hiệu trên Trang."
                ),
            )
        )

    hashtags = _HASHTAG.findall(text)
    if len(hashtags) > HASHTAG_SOFT_LIMIT:
        warnings.append(
            RenderWarning(
                code="MANY_HASHTAGS",
                message=(
                    f"Bài có {len(hashtags)} hashtag. Nhiều hơn "
                    f"{HASHTAG_SOFT_LIMIT} thường làm bài trông như spam."
                ),
            )
        )

    return warnings
