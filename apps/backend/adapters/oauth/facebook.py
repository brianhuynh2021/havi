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
#:
#: Cố ý KHÔNG xin `pages_read_user_content`: nội dung bình luận tới Havi qua
#: webhook `feed` (do `pages_manage_metadata` cấp), không phải bằng lệnh đọc
#: chủ động — nên quyền đó thừa, mà mỗi permission thừa là một câu phải trả lời
#: trong App Review.
#: - `pages_manage_posts`: đăng bài đã được người dùng duyệt.
#: - `pages_manage_engagement`: trả lời bình luận công khai.
#: - `pages_manage_metadata`: đăng ký Page nhận webhook.
#: - `pages_messaging`: nhận và trả lời Messenger trong cửa sổ Meta cho phép.
SCOPES = (
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
    "pages_manage_engagement",
    "pages_manage_metadata",
    "pages_messaging",
)

#: Quyền **không có thì không nối được**. Thiếu một trong ba là kết nối vô dụng
#: chứ không phải "thiếu một tính năng":
#:
#: - `pages_show_list` + `pages_read_engagement`: không có thì không lấy nổi
#:   Page token, tức là chẳng có gì để lưu.
#: - `pages_manage_metadata`: `exchange_code` kết thúc bằng đăng ký webhook.
#:   Thiếu nó thì Havi không bao giờ nhận được tin nhắn hay bình luận, và đó
#:   đúng là kịch bản "UI báo xanh mà Inbox im lặng" mà module này phải tránh.
REQUIRED_SCOPES = frozenset({
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_metadata",
})

#: Quyền bật thêm tính năng. Thiếu thì kênh vẫn nối được, chỉ là tính năng đó
#: tắt — chủ tiệm thấy rõ cái nào đang bật thay vì bị chặn ở cửa.
#: Xem `Capability` bên dưới để biết mỗi quyền mở ra cái gì.
OPTIONAL_SCOPES = frozenset({
    "pages_manage_posts",
    "pages_manage_engagement",
    "pages_messaging",
})

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
            granted = await self._granted_scopes(client, long_lived)
            pages = await self._list_pages(client, long_lived)
            page = _pick_page(pages)
            # `tasks` của Page nói chủ tiệm được làm gì trên chính Trang đó, độc
            # lập với quyền app. Trước đây thiếu một task là chặn; giờ nó thu
            # hẹp năng lực giống hệt quyền thiếu — cùng một cách xử lý, vì với
            # người dùng thì "app không được phép" và "tôi không được phép" đều
            # dẫn tới cùng một kết quả: tính năng đó tắt.
            tasks = set(page.get("tasks") or [])
            granted = frozenset(granted & _scopes_allowed_by_tasks(tasks))
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
                granted=granted,
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
            granted_scopes=tuple(sorted(granted)),
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

    async def _granted_scopes(self, client: httpx.AsyncClient, user_token: str) -> frozenset[str]:
        """Quyền chủ tiệm thực sự đã cấp, và chặn sớm nếu thiếu quyền lõi.

        Trước đây hàm này đòi đủ **cả bảy** quyền, thiếu một là ném lỗi và không
        nối được gì. Đó là all-or-nothing: chủ tiệm bấm cấp quyền xong, chờ, rồi
        bị đá về tay trắng chỉ vì thiếu một quyền phụ mà họ có thể không cần —
        ví dụ tiệm chưa dùng Messenger.

        Giờ chỉ `REQUIRED_SCOPES` mới chặn (xem docstring của nó: thiếu là kết
        nối vô dụng thật). Quyền tuỳ chọn thiếu thì kênh vẫn nối, tính năng
        tương ứng tắt, và `granted_scopes` đi theo connection để mọi nơi biết
        cái gì đang bật.
        """
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
        missing_required = sorted(REQUIRED_SCOPES - granted)
        if missing_required:
            raise OAuthPermanentError(
                self.platform,
                "Facebook chưa cấp quyền tối thiểu để nối Trang: "
                + ", ".join(missing_required),
            )
        return frozenset(granted & set(SCOPES))

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
        granted: frozenset[str],
    ) -> None:
        """Đăng ký Page nhận đúng những loại sự kiện quyền hiện có cho phép.

        Chỉ xin `messages` khi có `pages_messaging`: xin một field không có
        quyền thì Meta từ chối **cả lệnh**, làm mất luôn `feed` mà đáng lẽ đăng
        ký được. Nên lọc trước rồi mới gọi.
        """
        fields = [f for f in WEBHOOK_FIELDS if f != "messages" or "pages_messaging" in granted]
        if not fields:
            return
        body = await self._post(
            client,
            f"/{page_id}/subscribed_apps",
            params={"subscribed_fields": ",".join(fields)},
            access_token=page_token,
        )
        if body.get("success") is not True:
            raise OAuthPermanentError(
                self.platform,
                "Facebook chưa xác nhận đăng ký nhận tin cho Trang",
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


#: Task trên Page ↔ quyền app. Cùng một tính năng cần **cả hai**: app được cấp
#: quyền, và người cấp quyền có task đó trên chính Trang. Thiếu vế nào cũng dẫn
#: tới lỗi lúc gọi API, nên gộp chung một chỗ để không phải kiểm hai lần.
_TASK_FOR_SCOPE = {
    "pages_manage_posts": "CREATE_CONTENT",
    "pages_manage_engagement": "MODERATE",
    "pages_messaging": "MESSAGING",
}


def _scopes_allowed_by_tasks(tasks: set[str]) -> frozenset[str]:
    """Quyền còn dùng được sau khi soi task thật của Page."""
    return frozenset(
        scope
        for scope in SCOPES
        if _TASK_FOR_SCOPE.get(scope) is None or _TASK_FOR_SCOPE[scope] in tasks
    )


def _pick_page(pages: list[dict]) -> dict:
    """Chọn Page khi chủ tiệm quản lý nhiều Trang.

    Ưu tiên Page có task `CREATE_CONTENT` và ưu tiên Page thật (không chứa chữ sandbox)
    nếu chủ tiệm có cả trang thật lẫn trang thử nghiệm.
    """
    # Xếp hạng thay vì lọc bỏ: Trang chỉ có CREATE_CONTENT vẫn đăng bài được,
    # loại nó ra rồi báo "không có Trang nào" là sai sự thật. Nhiều task hơn thì
    # xếp trước, và Trang thật luôn hơn Trang sandbox khi cùng điểm.
    ranked = sorted(
        pages,
        key=lambda p: (
            len({"CREATE_CONTENT", "MESSAGING", "MODERATE"} & set(p.get("tasks") or [])),
            "sandbox" not in (p.get("name") or "").lower(),
        ),
        reverse=True,
    )
    return ranked[0]


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
