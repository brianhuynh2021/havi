"""Phân loại việc trong hàng đợi, và mức thiệt hại khi bỏ sót.

Vì sao cần phân loại
--------------------
Bỏ sót *"mấy giờ mở cửa"* và bỏ sót *"cho em xin báo giá"* tốn tiền khác nhau
hoàn toàn. Một hàng đợi xếp thuần theo thời gian sẽ đẩy câu hỏi giá của khách
xuống dưới ba câu hỏi giờ mở cửa đến sau — và người trực ca hết giờ trước khi
tới nó.

Vì sao là keyword chứ không phải LLM
-------------------------------------
Ba lý do, theo thứ tự quan trọng:

1. **Tốn tiền theo lượt.** Phân loại chạy trên *mọi* tin đến, gồm cả spam và tin
   một chữ. Gọi model cho từng tin là dòng chi phí lớn nhất mà không ai thấy.
2. **Không kiểm chứng được.** Một bộ keyword sai thì đọc `PRICE_TERMS` là biết
   sai ở đâu; một model phân loại sai thì không.
3. **Không cần đúng hoàn hảo.** Kết quả chỉ dùng để *xếp thứ tự* hàng đợi. Đoán
   nhầm một tin thành hỏi giá thì nó lên đầu sớm hơn — thiệt hại bằng không.
   Đoán nhầm theo chiều kia thì nó vẫn nằm trong hàng đợi, chỉ chậm hơn.

Khi nào nên đổi sang LLM: khi đo được rằng tin hỏi giá bị lọt xuống nhóm `OTHER`
đủ nhiều để mất khách. Trước lúc có số đó, đây là tối ưu hoá theo cảm giác.

Dấu tiếng Việt
--------------
Khách gõ điện thoại thường không có dấu: "bao nhieu tien", "gia bao nhieu". So
khớp trên bản đã bỏ dấu, nếu không bộ keyword chỉ bắt được nửa số tin thật.
"""

import re
import unicodedata
from collections.abc import Iterator
from enum import StrEnum

from core.enums import InboxItemType


class TicketCategory(StrEnum):
    """Loại việc. Giá trị lưu vào `inbox_items.category`."""

    #: Khách hỏi giá, báo giá, chi phí. Bỏ sót là mất khách đang muốn mua.
    PRICE = "price"
    #: Khách muốn đặt lịch, đặt bàn, giữ chỗ. Cũng là ý định mua.
    BOOKING = "booking"
    #: Khiếu nại, phàn nàn. Bỏ sót thì thiệt hại là uy tín, và nó lan.
    COMPLAINT = "complaint"
    #: Hỏi thông tin: giờ mở cửa, địa chỉ, còn hàng không.
    INFO = "info"
    #: Không khớp nhóm nào.
    OTHER = "other"


#: Thứ tự ưu tiên trong hàng đợi. Số nhỏ nổi lên trước.
#:
#: Khiếu nại xếp trên hỏi giá: một khách hỏi giá bị chậm thì có thể mất một đơn,
#: một khách khiếu nại bị bỏ mặc thì viết đánh giá một sao và mất nhiều đơn.
CATEGORY_PRIORITY: dict[TicketCategory, int] = {
    TicketCategory.COMPLAINT: 0,
    TicketCategory.PRICE: 1,
    TicketCategory.BOOKING: 2,
    TicketCategory.INFO: 3,
    TicketCategory.OTHER: 4,
}

#: Nhóm mà bỏ sót gây thiệt hại đo được bằng tiền hoặc uy tín. Báo cáo "tổn thất
#: tránh được" đếm riêng nhóm này — sót 12 tin hỏi giá là một câu bán hàng, sót
#: 12 tin hỏi giờ mở cửa thì không.
COSTLY_CATEGORIES = frozenset(
    {TicketCategory.PRICE, TicketCategory.BOOKING, TicketCategory.COMPLAINT}
)


def _fold(text: str) -> str:
    """Về chữ thường, bỏ dấu — để "gia bao nhieu" khớp cùng bộ keyword với "giá"."""
    lowered = text.casefold()
    decomposed = unicodedata.normalize("NFD", lowered)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    # `đ` không phải nguyên âm có dấu tổ hợp nên NFD không tách được.
    return stripped.replace("đ", "d")


#: Đã bỏ dấu sẵn — so khớp với chuỗi đã qua `_fold`, **theo từ** chứ không theo
#: chuỗi con.
#:
#: Vì sao phải theo từ: bản đầu khớp chuỗi con và `"hong"` bắt luôn `"khong"` —
#: nên gần như mọi tin tiếng Việt đều bị xếp thành khiếu nại. Đó là lý do một bộ
#: keyword đáng tin hơn một model phân loại: lỗi này đọc `PRICE_TERMS` là thấy,
#: còn model đoán sai thì không có gì để đọc.
#:
#: Và vì sao phần lớn là **cụm từ** chứ không phải từ đơn: tiếng Việt bỏ dấu có
#: rất nhiều từ trùng nhau. `"gia"` là cả `"giá"` lẫn `"gia đình"`/`"tham gia"`;
#: `"cham"` là cả `"chậm"` lẫn `"chăm sóc"`; `"tien"` là cả `"tiền"` lẫn
#: `"tiến"`/`"tiện"`. Từ đơn nào còn ở đây là từ đã kiểm không có nghĩa khác
#: thường gặp.
PRICE_TERMS = (
    "bao nhieu",
    "bao nhiu",
    "gia bao nhieu",
    "gia tien",
    "gia ca",
    "gia sao",
    "gia the nao",
    "bang gia",
    "bao gia",
    "chi phi",
    "hoc phi",
    "khuyen mai",
    "uu dai",
    "giam gia",
    "combo",
)

BOOKING_TERMS = (
    "dat lich",
    "dat ban",
    "dat phong",
    "dat cho",
    "book",
    "giu cho",
    "con cho",
    "con phong",
    "con ban",
    "dang ky",
    "ghi danh",
    "hen lich",
)

COMPLAINT_TERMS = (
    "that vong",
    "khong hai long",
    "phan anh",
    "khieu nai",
    "te qua",
    "qua te",
    "do qua",
    "qua do",
    "lau qua",
    "cham qua",
    "qua cham",
    "rat cham",
    "mat day",
    "bo mac",
    "lua dao",
    "hoan tien",
    "tra lai tien",
    "boi thuong",
    "bao xau",
    "danh gia 1 sao",
)

INFO_TERMS = (
    "may gio",
    "gio mo",
    "gio lam",
    "o dau",
    "dia chi",
    "duong nao",
    "co con",
    "con hang",
    "bao lau",
    "the nao",
)


#: Cụm keyword đã dựng sẵn thành regex khớp theo biên từ. Dựng một lần ở import
#: vì `classify` chạy trên mọi tin đến.
_PATTERNS: dict[str, re.Pattern[str]] = {
    name: re.compile(
        r"(?<![a-z0-9])(?:" + "|".join(re.escape(term) for term in terms) + r")(?![a-z0-9])"
    )
    for name, terms in (
        ("price", PRICE_TERMS),
        ("booking", BOOKING_TERMS),
        ("complaint", COMPLAINT_TERMS),
        ("info", INFO_TERMS),
    )
}


def classify(content: str) -> TicketCategory:
    """Phân loại một tin đến.

    Thứ tự kiểm **là** thứ tự ưu tiên: một tin vừa phàn nàn vừa hỏi giá thì tính
    là khiếu nại, vì đó là nửa cần xử lý cẩn thận hơn.

    Không có nhóm nào khớp thì trả `OTHER` chứ không đoán — hàng đợi vẫn giữ tin
    đó, chỉ là không được đẩy lên đầu.
    """
    folded = _fold(content)
    if _PATTERNS["complaint"].search(folded):
        return TicketCategory.COMPLAINT
    if _PATTERNS["price"].search(folded):
        return TicketCategory.PRICE
    if _PATTERNS["booking"].search(folded):
        return TicketCategory.BOOKING
    if _PATTERNS["info"].search(folded):
        return TicketCategory.INFO
    return TicketCategory.OTHER


def priority_of(category: str | None) -> int:
    """Thứ tự hàng đợi cho một giá trị `category` đọc từ database.

    Nhận `str | None` vì dòng ghi trước khi có cột này không có category, và một
    giá trị lạ (bộ phân loại cũ, sửa tay) không được làm sập màn làm việc — nó
    rơi xuống cuối hàng đợi.
    """
    if category is None:
        return CATEGORY_PRIORITY[TicketCategory.OTHER]
    try:
        return CATEGORY_PRIORITY[TicketCategory(category)]
    except ValueError:
        return CATEGORY_PRIORITY[TicketCategory.OTHER]


def is_costly(category: str | None) -> bool:
    """`True` khi bỏ sót việc này gây thiệt hại đo được."""
    if category is None:
        return False
    try:
        return TicketCategory(category) in COSTLY_CATEGORIES
    except ValueError:
        return False


class Inquiry:
    """Một sự kiện đã bóc tách, chuẩn hoá khỏi khác biệt giữa các loại webhook."""

    __slots__ = (
        "page_id",
        "message_id",
        "author_name",
        "text",
        "sender_id",
        "item_type",
    )

    def __init__(
        self,
        *,
        page_id: str,
        message_id: str,
        author_name: str,
        text: str,
        sender_id: str | None = None,
        item_type: InboxItemType = InboxItemType.MESSAGE,
    ):
        self.page_id = page_id
        self.message_id = message_id
        self.author_name = author_name
        self.text = text
        self.sender_id = sender_id
        self.item_type = item_type


def iter_inquiries(payload: dict) -> Iterator[Inquiry]:
    """Bóc `messaging` (tin nhắn) và `changes` (bình luận) ra cùng một hình dạng.

    Hàm thuần, không I/O — chỗ dễ sai nhất của webhook là hình dạng payload, nên
    tách ra để test được mà không cần dựng HTTP hay DB.
    """
    for entry in payload.get("entry", []) or []:
        page_id = str(entry.get("id") or "")
        if not page_id:
            continue

        for messaging in entry.get("messaging", []) or []:
            message = messaging.get("message") or {}
            text = (message.get("text") or "").strip()
            message_id = message.get("mid")
            sender_id = (messaging.get("sender") or {}).get("id")
            if not text or not message_id:
                continue
            # Bỏ echo: tin do chính Page gửi cũng quay lại qua webhook, nhận vào
            # thì inbox đầy những câu của chính chủ tiệm.
            if messaging.get("message", {}).get("is_echo"):
                continue
            yield Inquiry(
                page_id=page_id,
                message_id=str(message_id),
                author_name=f"Khách {str(sender_id)[-4:]}" if sender_id else "Khách",
                text=text,
                sender_id=str(sender_id) if sender_id else None,
            )

        for change in entry.get("changes", []) or []:
            if change.get("field") != "feed":
                continue
            value = change.get("value") or {}
            if value.get("item") != "comment" or value.get("verb") != "add":
                continue
            text = (value.get("message") or "").strip()
            comment_id = value.get("comment_id")
            if not text or not comment_id:
                continue
            author = (value.get("from") or {}).get("name") or "Khách"
            from_id = (value.get("from") or {}).get("id")
            yield Inquiry(
                page_id=page_id,
                message_id=str(comment_id),
                author_name=author,
                text=text,
                sender_id=str(from_id) if from_id else None,
                item_type=InboxItemType.COMMENT,
            )
