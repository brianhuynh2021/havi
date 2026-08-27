"""Facebook OAuth qua Graph API — đổi `code` lấy **Page access token**.

Năm bước, không bỏ được bước nào:

1. `code` → **user token ngắn hạn** (~1–2 giờ).
2. Đổi tiếp sang **user token dài hạn** (~60 ngày). Bỏ bước này thì Page token
   lấy ở bước 3 cũng ngắn hạn theo, và kênh chết sau vài giờ — chủ tiệm sẽ thấy
   bài đăng hỏng vào tối hôm sau mà không hiểu vì sao.
3. Kiểm tra tất cả quyền Havi thật sự cần đã được cấp.
4. `/me/accounts` → danh sách Page kèm **Page token của từng Page**. Đăng bài
   lên Page phải dùng token của Page đó, không phải user token.
5. Đăng ký Page với webhook `messages,feed`. Chỉ sau khi Meta xác nhận bước này
   kết nối mới được lưu; nếu không, UI sẽ báo xanh trong khi Inbox không nhận gì.

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

from adapters.meta_graph import GRAPH_BASE, GRAPH_VERSION
from adapters.oauth.base import (
    OAuthAccount,
    OAuthClientPort,
    OAuthPermanentError,
    OAuthTemporaryError,
)
from core.config import Settings
from core.enums import Platform

logger = logging.getLogger(__name__)

_DIALOG_URL = f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"

#: Quyền tối thiểu cho đúng các khả năng Facebook đang có trong Havi. Xin đúng
#: những gì cần dùng — mỗi
#: permission thừa là một câu hỏi phải trả lời trong App Review, và App Review
#: là rủi ro chặn pilot (ROADMAP §10).
#:
#: - `pages_show_list`: đọc danh sách Page chủ tiệm quản lý.
#: - `pages_read_engagement`: đọc tên/thông tin Page (bắt buộc đi kèm khi lấy
#:   Page token).
#: - `pages_read_user_content`: nhận nội dung bình luận của người dùng.
#: - `pages_manage_posts`: đăng bài đã được người dùng duyệt.
#: - `pages_manage_engagement`: trả lời bình luận công khai.
#: - `pages_manage_metadata`: đăng ký Page nhận webhook.
#: - `pages_messaging`: nhận và trả lời Messenger trong cửa sổ Meta cho phép.
SCOPES = (
    "pages_show_list",
    "pages_read_engagement",
    "pages_read_user_content",
    "pages_manage_posts",
    "pages_manage_engagement",
    "pages_manage_metadata",
    "pages_messaging",
)

WEBHOOK_FIELDS = ("messages", "feed")

#: Retry được: rate limit và lỗi phía Facebook. Cùng tập với LLM adapter.
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class FacebookOAuthClient(OAuthClientPort):
    def __init__(self, settings: Settings, *, timeout_seconds: float = 20.0) -> None:
        self._client_id = settings.facebook_client_id
        self._client_secret = settings.facebook_client_secret
        self._redirect_uri = settings.facebook_redirect_uri
        self._config_id = settings.facebook_config_id
        self._webhook_verify_token = settings.meta_webhook_verify_token
        self._env = settings.env
        self._timeout = timeout_seconds

    @property
    def platform(self) -> Platform:
        return Platform.FACEBOOK

    @property
    def is_configured(self) -> bool:
        # Public Havi includes Inbox, so an OAuth-only setup is incomplete. A
        # local developer may still exercise OAuth with a tunnel or test the
        # adapter against MockTransport before any public webhook exists.
        public_webhook_ready = self._env == "local" or bool(self._webhook_verify_token)
        return bool(self._client_id and self._client_secret and public_webhook_ready)

    def authorization_url(self, *, state: str) -> str:
        """URL màn hình cấp quyền.

        Hai kiểu app, hai cách khai quyền — và chọn sai thì Facebook trả
        `Invalid Scopes` ở bước callback chứ không báo lúc dựng URL:

        - **Facebook Login for Business** (app tạo mới hiện nay): quyền khai sẵn
          trong một *Configuration* trên dashboard, request chỉ gửi `config_id`.
          Gửi kèm `scope` là bị từ chối.
        - **Facebook Login** thường: gửi `scope` trực tiếp.

        Nên `HAVI_FACEBOOK_CONFIG_ID` có thì đi đường Business, không có thì giữ
        nguyên đường cũ — cùng một adapter chạy được cả hai.
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "state": state,
            "response_type": "code",
            "auth_type": "rerequest",
        }
        if self._config_id:
            params["config_id"] = self._config_id
        else:
            params["scope"] = ",".join(SCOPES)
        return f"{_DIALOG_URL}?" + urlencode(params)

    async def exchange_code(self, code: str) -> OAuthAccount:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            short_lived = await self._code_to_token(client, code)
            long_lived, expires_at = await self._to_long_lived(client, short_lived)
            external_user_id = await self._get_external_user_id(client, long_lived)
            await self._ensure_permissions(client, long_lived)
            pages = await self._list_pages(client, long_lived)
            page = _pick_page(pages)
            tasks = set(page.get("tasks") or [])
            if not {"CREATE_CONTENT", "MESSAGING", "MODERATE"}.issubset(tasks):
                raise OAuthPermanentError(
                    self.platform,
                    "Tài khoản chưa có đủ quyền đăng bài, nhắn tin và quản lý "
                    "bình luận trên Trang đã chọn",
                )
            page_token = page.get("access_token")
            if not page_token:
                # Page hiện ra nhưng không kèm token khi người dùng không có
                # đủ task trên Page. Lưu lúc này sẽ tạo kết nối giả.
                raise OAuthPermanentError(
                    self.platform,
                    "Trang chưa cấp đủ quyền vận hành — bạn nối lại và giữ "
                    "nguyên các ô tích quyền nhé",
                )
            await self._subscribe_page_webhooks(
                client,
                page_id=str(page["id"]),
                page_token=str(page_token),
            )

        return OAuthAccount(
            external_account_id=str(page["id"]),
            account_name=page.get("name") or "Trang Facebook",
            access_token=page_token,
            external_user_id=external_user_id,
            # Page token đổi từ user token dài hạn không hết hạn theo lịch (xem
            # docstring module). Ghi `expires_at` của *user token* vào đây sẽ
            # làm UI báo "sắp hết hạn" sai — để None và dựa vào lỗi lúc đăng.
            expires_at=None,
        )

    # --- Năm bước Graph ------------------------------------------------------

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
                self.platform, "Facebook không trả access token — bạn nối lại từ đầu nhé"
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
                self.platform, "Không đổi được token dài hạn — bạn nối lại từ đầu nhé"
            )
        expires_in = body.get("expires_in")
        expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in)) if expires_in else None
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
                "Tài khoản Facebook này chưa quản lý Trang nào. Bạn tạo Trang rồi nối lại nhé",
            )
        return pages

    async def _ensure_permissions(self, client: httpx.AsyncClient, user_token: str) -> None:
        """Reject partial consent before it can become a green connection."""
        body = await self._get(
            client,
            "/me/permissions",
            {"access_token": user_token},
        )
        granted = {
            str(item.get("permission"))
            for item in body.get("data") or []
            if item.get("status") == "granted"
        }
        missing = [scope for scope in SCOPES if scope not in granted]
        if missing:
            raise OAuthPermanentError(
                self.platform,
                "Facebook chưa cấp đủ quyền cho Havi: " + ", ".join(missing),
            )

    async def _get_external_user_id(self, client: httpx.AsyncClient, user_token: str) -> str:
        """Capture Meta's app-scoped user ID for authenticated deletion requests."""
        body = await self._get(
            client,
            "/me",
            {"access_token": user_token, "fields": "id"},
        )
        external_user_id = body.get("id")
        if not external_user_id:
            raise OAuthPermanentError(
                self.platform,
                "Facebook không trả mã người cấp quyền — chưa thể nối Trang an toàn",
            )
        return str(external_user_id)

    async def _subscribe_page_webhooks(
        self,
        client: httpx.AsyncClient,
        *,
        page_id: str,
        page_token: str,
    ) -> None:
        """Subscribe the selected Page to the two event types Havi consumes."""
        body = await self._post(
            client,
            f"/{page_id}/subscribed_apps",
            params={"subscribed_fields": ",".join(WEBHOOK_FIELDS)},
            access_token=page_token,
        )
        if body.get("success") is not True:
            raise OAuthPermanentError(
                self.platform,
                "Facebook chưa xác nhận đăng ký Messenger và bình luận cho Trang",
            )

    # --- HTTP ----------------------------------------------------------------

    async def _get(self, client: httpx.AsyncClient, path: str, params: dict) -> dict:
        """GET Graph API và chuẩn hoá lỗi về hai loại.

        `params` chứa secret và token — không bao giờ đưa nó vào message lỗi
        hay log. Chỉ path được nêu tên.
        """
        try:
            response = await client.get(f"{GRAPH_BASE}{path}", params=params)
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
                f"Facebook đang bận (HTTP {response.status_code}) — bạn thử lại sau ít phút",
            )
        if response.status_code >= 400:
            raise OAuthPermanentError(self.platform, _graph_error_message(response, path))

        try:
            return response.json()
        except ValueError as exc:
            raise OAuthTemporaryError(
                self.platform, f"Facebook trả dữ liệu không đọc được ở {path}"
            ) from exc

    async def _post(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        params: dict,
        access_token: str,
    ) -> dict:
        """POST Graph without putting the Page token in the URL or error text."""
        try:
            response = await client.post(
                f"{GRAPH_BASE}{path}",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
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
                f"Facebook đang bận (HTTP {response.status_code}) — bạn thử lại sau ít phút",
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

    Ưu tiên Page có task `CREATE_CONTENT` và ưu tiên Page thật (không chứa chữ sandbox)
    nếu chủ tiệm có cả trang thật lẫn trang thử nghiệm.
    """
    required_tasks = {"CREATE_CONTENT", "MESSAGING", "MODERATE"}
    non_sandbox_actionable = [
        p
        for p in pages
        if "sandbox" not in (p.get("name") or "").lower()
        and required_tasks.issubset(set(p.get("tasks") or []))
    ]
    if non_sandbox_actionable:
        return non_sandbox_actionable[0]

    for page in pages:
        tasks = set(page.get("tasks") or [])
        if required_tasks.issubset(tasks):
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
