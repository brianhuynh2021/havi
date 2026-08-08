"""Facebook OAuth qua Graph API — đổi `code` lấy **Page access token**.

Ba bước, không bỏ được bước nào:

1. `code` → **user token ngắn hạn** (~1–2 giờ).
2. Đổi tiếp sang **user token dài hạn** (~60 ngày). Bỏ bước này thì Page token
   lấy ở bước 3 cũng ngắn hạn theo, và kênh chết sau vài giờ — chủ tiệm sẽ thấy
   bài đăng hỏng vào tối hôm sau mà không hiểu vì sao.
3. `/me/accounts` → danh sách Page kèm **Page token của từng Page**. Đăng bài
   lên Page phải dùng token của Page đó, không phải user token.

Điều đáng chú ý nhất: **Page token đổi từ user token dài hạn thì không có hạn
dùng** (Facebook không trả `expires_in`). Nó chỉ chết khi chủ tiệm đổi mật khẩu,
gỡ app, hoặc bị Facebook thu hồi quyền — tức là không đoán trước được bằng
`expires_at`. Vì vậy đường phát hiện mất kết nối duy nhất đáng tin là lỗi
`AuthPermissionError` lúc đăng bài, và `PublishService` đã đánh dấu connection
`expired` ngay khi gặp lỗi đó.

Chọn Page nào khi chủ tiệm quản lý nhiều Page: xem `_pick_page`.
"""

import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from adapters.oauth.base import (
    OAuthAccount,
    OAuthClientPort,
    OAuthPermanentError,
    OAuthTemporaryError,
)
from core.config import Settings
from core.enums import Platform

logger = logging.getLogger(__name__)

GRAPH_VERSION = "v21.0"
_GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
_DIALOG_URL = f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"

#: Quyền tối thiểu để đăng bài lên Page. Xin đúng những gì cần dùng — mỗi
#: permission thừa là một câu hỏi phải trả lời trong App Review, và App Review
#: là rủi ro chặn pilot (ROADMAP §10).
#:
#: - `pages_show_list`: đọc danh sách Page chủ tiệm quản lý.
#: - `pages_read_engagement`: đọc tên/thông tin Page (bắt buộc đi kèm khi lấy
#:   Page token).
#: - `pages_manage_posts`: đăng bài. Đây là quyền phải qua App Review.
SCOPES = ("pages_show_list", "pages_read_engagement", "pages_manage_posts")

#: Retry được: rate limit và lỗi phía Facebook. Cùng tập với LLM adapter.
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class FacebookOAuthClient(OAuthClientPort):
    def __init__(self, settings: Settings, *, timeout_seconds: float = 20.0) -> None:
        self._client_id = settings.facebook_client_id
        self._client_secret = settings.facebook_client_secret
        self._redirect_uri = settings.facebook_redirect_uri
        self._timeout = timeout_seconds

    @property
    def platform(self) -> Platform:
        return Platform.FACEBOOK

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def authorization_url(self, *, state: str) -> str:
        return f"{_DIALOG_URL}?" + urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "state": state,
                "scope": ",".join(SCOPES),
                "response_type": "code",
            }
        )

    async def exchange_code(self, code: str) -> OAuthAccount:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            short_lived = await self._code_to_token(client, code)
            long_lived, expires_at = await self._to_long_lived(client, short_lived)
            pages = await self._list_pages(client, long_lived)

        page = _pick_page(pages)
        page_token = page.get("access_token")
        if not page_token:
            # Xảy ra khi user cấp `pages_show_list` nhưng từ chối
            # `pages_manage_posts` ở màn hình chọn quyền của Facebook: Page
            # hiện ra nhưng không kèm token. Nối vào lúc này thì chấm xanh mà
            # đăng bài hỏng — thà chặn ngay ở đây.
            raise OAuthPermanentError(
                self.platform,
                "Trang chưa cấp quyền đăng bài — chị bấm nối lại và giữ nguyên "
                "các ô tích quyền giúp em nhé",
            )

        return OAuthAccount(
            external_account_id=str(page["id"]),
            account_name=page.get("name") or "Trang Facebook",
            access_token=page_token,
            # Page token đổi từ user token dài hạn không hết hạn theo lịch (xem
            # docstring module). Ghi `expires_at` của *user token* vào đây sẽ
            # làm UI báo "sắp hết hạn" sai — để None và dựa vào lỗi lúc đăng.
            expires_at=None,
        )

    # --- Ba bước Graph -------------------------------------------------------

    async def _code_to_token(self, client: httpx.AsyncClient, code: str) -> str:
        body = await self._get(
            client,
            "/oauth/access_token",
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": self._redirect_uri,
                "code": code,
            },
        )
        token = body.get("access_token")
        if not token:
            raise OAuthPermanentError(
                self.platform, "Facebook không trả access token — chị nối lại từ đầu nhé"
            )
        return token

    async def _to_long_lived(
        self, client: httpx.AsyncClient, short_lived: str
    ) -> tuple[str, datetime | None]:
        body = await self._get(
            client,
            "/oauth/access_token",
            {
                "grant_type": "fb_exchange_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "fb_exchange_token": short_lived,
            },
        )
        token = body.get("access_token")
        if not token:
            raise OAuthPermanentError(
                self.platform, "Không đổi được token dài hạn — chị nối lại từ đầu nhé"
            )
        expires_in = body.get("expires_in")
        expires_at = (
            datetime.now(UTC) + timedelta(seconds=int(expires_in)) if expires_in else None
        )
        return token, expires_at

    async def _list_pages(self, client: httpx.AsyncClient, user_token: str) -> list[dict]:
        body = await self._get(
            client,
            "/me/accounts",
            {"access_token": user_token, "fields": "id,name,access_token,tasks"},
        )
        pages = body.get("data") or []
        if not pages:
            raise OAuthPermanentError(
                self.platform,
                "Tài khoản Facebook này chưa quản lý Trang nào. Chị tạo Trang cho "
                "tiệm rồi nối lại giúp em nhé",
            )
        return pages

    # --- HTTP ----------------------------------------------------------------

    async def _get(self, client: httpx.AsyncClient, path: str, params: dict) -> dict:
        """GET Graph API và chuẩn hoá lỗi về hai loại.

        `params` chứa secret và token — không bao giờ đưa nó vào message lỗi
        hay log. Chỉ path được nêu tên.
        """
        try:
            response = await client.get(f"{_GRAPH_BASE}{path}", params=params)
        except httpx.TimeoutException as exc:
            raise OAuthTemporaryError(
                self.platform, f"Facebook không phản hồi sau {self._timeout}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise OAuthTemporaryError(
                self.platform, f"Lỗi kết nối tới Facebook: {type(exc).__name__}"
            ) from exc

        if response.status_code in _TRANSIENT_STATUSES:
            raise OAuthTemporaryError(
                self.platform,
                f"Facebook đang bận (HTTP {response.status_code}) — chị thử lại sau ít phút",
            )
        if response.status_code >= 400:
            raise OAuthPermanentError(self.platform, _graph_error_message(response, path))

        try:
            return response.json()
        except ValueError as exc:
            raise OAuthTemporaryError(
                self.platform, f"Facebook trả dữ liệu không đọc được ở {path}"
            ) from exc


def _pick_page(pages: list[dict]) -> dict:
    """Chọn Page khi chủ tiệm quản lý nhiều Trang.

    Ưu tiên Page có task `CREATE_CONTENT` — Page mà tài khoản này thật sự đăng
    bài được. Chủ tiệm hay được add vào Page của người khác với vai trò
    Analyst/Advertiser (chỉ xem), nối nhầm vào đó thì mọi bài đều hỏng.

    Còn lại lấy Page đầu danh sách. Đây là chỗ MVP cố ý đơn giản: đúng cho
    trường hợp phổ biến (chủ tiệm có một Trang). Chọn Trang trong UI nằm ở
    P1 — khi có, `exchange_code` sẽ nhận thêm `page_id` mong muốn.
    """
    for page in pages:
        tasks = page.get("tasks") or []
        if "CREATE_CONTENT" in tasks:
            return page
    return pages[0]


def _graph_error_message(response: httpx.Response, path: str) -> str:
    """Rút message từ body lỗi Graph, có kiểm soát độ dài.

    Không đổ nguyên `response.text` vào detail: body lỗi của Graph đôi khi vọng
    lại tham số đã gửi, mà tham số đó chứa `client_secret` và access token.
    Chỉ lấy đúng `error.message` và cắt ngắn.
    """
    try:
        error = response.json().get("error") or {}
    except ValueError:
        error = {}
    message = str(error.get("message") or "")[:200]
    if not message:
        return f"Facebook từ chối yêu cầu ở {path} (HTTP {response.status_code})"
    return message
