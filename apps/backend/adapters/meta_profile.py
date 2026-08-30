"""Tra tên khách nhắn tin từ Graph API.

Webhook `messages` của Meta chỉ mang PSID, không mang tên. Không tra thì inbox
chỉ hiện "Khách 2310" — chủ tiệm nhìn vào không biết ai đang nhắn, mà đó lại
đúng là thứ đầu tiên cần biết khi mở inbox.

Tra tên là *bổ sung*, không phải điều kiện để nhận tin: Graph lỗi, hết quyền,
hay timeout đều không được phép làm mất tin nhắn của khách. Nên mọi lỗi ở đây
đều nuốt và trả `None`, để chỗ gọi lùi về nhãn "Khách 2310" như cũ.
"""

import logging

import httpx

from adapters.meta_graph import GRAPH_BASE

logger = logging.getLogger("havi.meta_profile")


async def fetch_sender_name(
    *,
    psid: str,
    page_token: str,
    timeout_seconds: float = 5.0,
) -> str | None:
    """Trả tên hiển thị của người nhắn, hoặc `None` nếu không tra được.

    Timeout ngắn (5s, không phải 15-20s như publish): đây là thứ làm cho đẹp,
    không đáng để giữ một tin nhắn khách nằm chờ trong queue.

    Token đi ở header `Authorization` chứ không phải query string — query string
    bị ghi nguyên vào access log của mọi proxy trên đường.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(
                f"{GRAPH_BASE}/{psid}",
                params={"fields": "name"},
                headers={"Authorization": f"Bearer {page_token}"},
            )
    except httpx.HTTPError as exc:
        # Chỉ nêu loại lỗi, không nêu nội dung: response lỗi của Graph có thể
        # mang theo token trong echo lại request.
        logger.warning("meta_profile.fetch_failed psid=%s error=%s", psid, type(exc).__name__)
        return None

    if response.status_code != 200:
        logger.warning("meta_profile.fetch_rejected psid=%s status=%s", psid, response.status_code)
        return None

    try:
        name = (response.json() or {}).get("name")
    except ValueError:
        logger.warning("meta_profile.bad_json psid=%s", psid)
        return None

    if not isinstance(name, str) or not name.strip():
        return None
    return name.strip()
