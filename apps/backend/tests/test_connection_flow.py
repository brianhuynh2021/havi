"""Nối kênh Facebook: signed state, đổi code, phân loại lỗi Graph, redaction.

Không gọi mạng thật — Graph API được thay bằng `MockTransport` của httpx, tức là
adapter vẫn chạy nguyên vẹn (dựng request, đọc response, phân loại lỗi) chỉ có
tầng socket là giả. Mock ở tầng `httpx.AsyncClient` thì test mất đúng phần cần
kiểm: việc dịch response của Facebook.

Nhóm test quan trọng nhất ở đây là `TestTokenRedaction`: token Facebook là chìa
khoá đăng bài lên Trang của khách, và đường lộ token dễ nhất không phải là hack
mà là một message lỗi vô tình mang nó vào log hoặc vào cột `failure_detail`.
"""

import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.oauth.base import (
    OAuthAccount,
    OAuthClientPort,
    OAuthPermanentError,
    OAuthTemporaryError,
)
from adapters.oauth.facebook import SCOPES, FacebookOAuthClient, _pick_page
from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from adapters.publishers.facebook import FacebookPublisher
from application.services.connection_service import (
    ConnectionNotFound,
    ConnectionService,
    NotWorkspaceMember,
    PlatformNotConfigured,
    PlatformNotSupported,
)
from core.config import Settings
from core.enums import ConnectionStatus, Industry, Platform, WorkspaceRole
from core.oauth_state import InvalidOAuthState, create_oauth_state
from domain.models.user import User
from domain.models.workspace import Workspace, WorkspaceMember
from domain.ports.publisher import (
    AuthPermissionError,
    PublishRequest,
    TemporaryPublishError,
    ValidationPublishError,
)

pytestmark = pytest.mark.anyio

PAGE_TOKEN = "EAAG-page-token-bi-mat"
USER_TOKEN = "EAAG-user-token-bi-mat"


def _settings(**overrides) -> Settings:
    # `facebook_config_id` khai tường minh là "" chứ không bỏ trống: Settings đọc
    # cả `.env` thật, nên máy dev đã cấu hình Login for Business sẽ khiến test
    # nhánh "Login thường" chạy sai nhánh và đỏ — test phải độc lập với môi trường.
    base = {
        "facebook_client_id": "app-123",
        "facebook_client_secret": "secret-456",
        "facebook_redirect_uri": "https://api.havi.vn/connections/facebook/callback",
        "facebook_config_id": "",
        "jwt_secret": "test-secret-du-dai-de-ky",
        "token_encryption_key": "3Vn8Qm2xLp7YtZa1Rk4Wc6Bd9Ef0Gh5Jj2Kl3Mn4Op8=",
    }
    return Settings(**{**base, **overrides})


# --- Graph API giả -----------------------------------------------------------


def _oauth_transport(*, pages: list[dict] | None = None) -> httpx.MockTransport:
    """Graph API chạy đúng luồng 3 bước: code → short → long → /me/accounts."""
    if pages is None:
        pages = [{"id": "page-1", "name": "Spa An Nhiên", "access_token": PAGE_TOKEN,
                  "tasks": ["CREATE_CONTENT", "MANAGE"]}]

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        if request.url.path.endswith("/oauth/access_token"):
            if params.get("grant_type") == "fb_exchange_token":
                return httpx.Response(200, json={"access_token": USER_TOKEN, "expires_in": 5184000})
            return httpx.Response(200, json={"access_token": "short-lived", "expires_in": 3600})
        if request.url.path.endswith("/me/accounts"):
            return httpx.Response(200, json={"data": pages})
        return httpx.Response(404, json={"error": {"message": "khong co route", "code": 803}})

    return httpx.MockTransport(handler)


def _patch_client(monkeypatch, transport: httpx.MockTransport, module) -> None:
    """Ép AsyncClient trong module dùng transport giả, giữ nguyên phần còn lại."""
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(module.httpx, "AsyncClient", factory)


class _StubOAuthClient(OAuthClientPort):
    """Client tối thiểu cho nền tảng chưa có adapter thật, chỉ để test đi qua
    `_client_for` và tới được chỗ kiểm state."""

    def __init__(self, platform: Platform) -> None:
        self._platform = platform

    @property
    def platform(self) -> Platform:
        return self._platform

    @property
    def is_configured(self) -> bool:
        return True

    def authorization_url(self, *, state: str) -> str:
        return f"https://stub.test/oauth?state={state}"

    async def exchange_code(self, code: str) -> OAuthAccount:
        return OAuthAccount(
            external_account_id="stub-1", account_name="Stub", access_token="stub-token"
        )


# --- Fixtures DB -------------------------------------------------------------


async def _workspace_with_member(session: AsyncSession) -> tuple[Workspace, User]:
    owner = User(email=f"{uuid.uuid4().hex[:10]}@spa.vn", name="Chị Hương")
    session.add(owner)
    await session.flush()

    ws = Workspace(name="Spa An Nhiên", industry=Industry.SPA, owner_user_id=owner.id)
    session.add(ws)
    await session.flush()

    session.add(
        WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role=WorkspaceRole.OWNER)
    )
    await session.flush()
    return ws, owner


def _service(session: AsyncSession, monkeypatch, *, transport=None, settings=None):
    settings = settings or _settings()
    client = FacebookOAuthClient(settings)
    if transport is not None:
        import adapters.oauth.facebook as fb_module

        _patch_client(monkeypatch, transport, fb_module)
    return ConnectionService(
        connections=ConnectionRepository(session),
        members=WorkspaceMemberRepository(session),
        oauth_clients={Platform.FACEBOOK: client},
        settings=settings,
    )


class TestAuthorizationUrl:
    """Hai kiểu app Facebook khai quyền theo hai cách khác nhau.

    Chọn sai không lộ ra lúc dựng URL — Facebook nhận request, hiện màn cấp
    quyền, rồi mới trả `Invalid Scopes` ở bước callback. Nên phải chốt bằng test
    thay vì thử tay từng lần.
    """

    def _params(self, url: str) -> dict[str, str]:
        from urllib.parse import parse_qs, urlparse

        return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}

    def test_login_for_business_gui_config_id_khong_gui_scope(self):
        """Facebook Login for Business: quyền nằm trong Configuration trên
        dashboard. Gửi kèm `scope` là bị từ chối."""
        client = FacebookOAuthClient(_settings(facebook_config_id="cfg-789"))
        params = self._params(client.authorization_url(state="st"))

        assert params["config_id"] == "cfg-789"
        assert "scope" not in params

    def test_login_thuong_gui_scope_khi_khong_co_config_id(self):
        """App dùng Facebook Login thường vẫn phải chạy được — giữ đường cũ."""
        client = FacebookOAuthClient(_settings())
        params = self._params(client.authorization_url(state="st"))

        assert "config_id" not in params
        assert params["scope"] == "pages_show_list,pages_read_engagement,pages_manage_posts"

    def test_luon_kem_state_va_redirect_uri(self):
        """Hai nhánh đều phải mang `state` (chống CSRF) và đúng redirect URI."""
        for settings in (_settings(), _settings(facebook_config_id="cfg-789")):
            params = self._params(
                FacebookOAuthClient(settings).authorization_url(state="st-abc")
            )
            assert params["state"] == "st-abc"
            assert params["redirect_uri"] == settings.facebook_redirect_uri
            assert params["response_type"] == "code"


# --- OAuth state: chống CSRF -------------------------------------------------


class TestOAuthState:
    """State là thứ duy nhất chứng minh callback thuộc về đúng người đã bấm nối.

    Callback không có JWT (Facebook điều hướng trình duyệt tới), nên mọi test ở
    đây kiểm đúng một câu hỏi: kẻ tấn công có nối được Page của mình vào tiệm
    của người khác không.
    """

    async def test_start_tra_url_co_state_va_du_scope(self, db_session, monkeypatch):
        ws, owner = await _workspace_with_member(db_session)
        service = _service(db_session, monkeypatch)

        url, state = service.start(
            workspace_id=ws.id, user_id=owner.id, platform=Platform.FACEBOOK
        )

        assert "facebook.com" in url and f"state={state}" in url
        for scope in SCOPES:
            assert scope in url
        # Quyền đăng bài phải có mặt, nếu không nối xong vẫn không đăng được.
        assert "pages_manage_posts" in url

    async def test_state_gia_mao_bi_tu_choi(self, db_session, monkeypatch):
        service = _service(db_session, monkeypatch, transport=_oauth_transport())

        with pytest.raises(InvalidOAuthState):
            await service.complete(
                platform=Platform.FACEBOOK, code="code-hop-le", state="state-bia-dat"
            )

    async def test_state_ky_bang_khoa_khac_bi_tu_choi(self, db_session, monkeypatch):
        """Kẻ tấn công tự ký state bằng khoá của mình thì không lọt."""
        ws, owner = await _workspace_with_member(db_session)
        state_gia = create_oauth_state(
            workspace_id=ws.id,
            user_id=owner.id,
            platform=Platform.FACEBOOK,
            settings=_settings(jwt_secret="khoa-cua-ke-tan-cong"),
        )
        service = _service(db_session, monkeypatch, transport=_oauth_transport())

        with pytest.raises(InvalidOAuthState):
            await service.complete(
                platform=Platform.FACEBOOK, code="code", state=state_gia
            )

    async def test_state_cua_facebook_khong_dung_lai_o_callback_zalo(self, db_session):
        """State phát cho Facebook không được tái sử dụng ở callback nền tảng khác.

        Dựng sẵn một client Zalo giả để đi qua được `_client_for` — nếu không,
        test dừng ở `PlatformNotSupported` và không kiểm được điều cần kiểm.
        """
        ws, owner = await _workspace_with_member(db_session)
        settings = _settings()
        state_fb = create_oauth_state(
            workspace_id=ws.id, user_id=owner.id, platform=Platform.FACEBOOK,
            settings=settings,
        )
        service = ConnectionService(
            connections=ConnectionRepository(db_session),
            members=WorkspaceMemberRepository(db_session),
            oauth_clients={Platform.ZALO_OA: _StubOAuthClient(Platform.ZALO_OA)},
            settings=settings,
        )

        with pytest.raises(InvalidOAuthState):
            await service.complete(
                platform=Platform.ZALO_OA, code="code", state=state_fb
            )

    async def test_nguoi_da_bi_go_khoi_workspace_khong_noi_duoc(
        self, db_session, monkeypatch
    ):
        """State sống 10 phút — đủ để ai đó bị gỡ quyền ngay sau khi bấm nối."""
        ws, _ = await _workspace_with_member(db_session)
        nguoi_la = User(email=f"{uuid.uuid4().hex[:8]}@x.vn", name="Người lạ")
        db_session.add(nguoi_la)
        await db_session.flush()

        settings = _settings()
        state = create_oauth_state(
            workspace_id=ws.id, user_id=nguoi_la.id, platform=Platform.FACEBOOK,
            settings=settings,
        )
        service = _service(db_session, monkeypatch, transport=_oauth_transport(),
                           settings=settings)

        with pytest.raises(NotWorkspaceMember):
            await service.complete(platform=Platform.FACEBOOK, code="code", state=state)


# --- Nối kênh end-to-end -----------------------------------------------------


class TestCompleteConnection:
    async def test_noi_thanh_cong_luu_page_token_da_ma_hoa(self, db_session, monkeypatch):
        ws, owner = await _workspace_with_member(db_session)
        settings = _settings()
        state = create_oauth_state(
            workspace_id=ws.id, user_id=owner.id, platform=Platform.FACEBOOK,
            settings=settings,
        )
        service = _service(db_session, monkeypatch, transport=_oauth_transport(),
                           settings=settings)

        result = await service.complete(
            platform=Platform.FACEBOOK, code="code-tu-facebook", state=state
        )

        assert result.status is ConnectionStatus.CONNECTED
        assert result.account_name == "Spa An Nhiên"
        assert result.connected_by == owner.id

        repo = ConnectionRepository(db_session)
        row = await repo.get(workspace_id=ws.id, platform=Platform.FACEBOOK)
        assert row is not None
        assert row.external_account_id == "page-1"
        # Lưu Page token, KHÔNG phải user token — đăng lên Page cần token Page.
        assert repo.read_access_token(row) == PAGE_TOKEN
        # Trong DB là bản mã, không phải chữ thường.
        assert PAGE_TOKEN not in row.access_token_encrypted

    async def test_page_token_khong_bao_gio_ra_response_schema(
        self, db_session, monkeypatch
    ):
        ws, owner = await _workspace_with_member(db_session)
        settings = _settings()
        state = create_oauth_state(
            workspace_id=ws.id, user_id=owner.id, platform=Platform.FACEBOOK,
            settings=settings,
        )
        service = _service(db_session, monkeypatch, transport=_oauth_transport(),
                           settings=settings)

        result = await service.complete(
            platform=Platform.FACEBOOK, code="code", state=state
        )

        dumped = result.model_dump_json()
        assert PAGE_TOKEN not in dumped and USER_TOKEN not in dumped
        assert "token" not in dumped.lower()

    async def test_noi_lai_cap_nhat_ban_ghi_cu_va_xoa_ly_do_hong(
        self, db_session, monkeypatch
    ):
        """Nối lại sau khi token chết: phải về `connected` và sạch failure_reason."""
        ws, owner = await _workspace_with_member(db_session)
        repo = ConnectionRepository(db_session)
        cu = await repo.upsert(
            workspace_id=ws.id, platform=Platform.FACEBOOK, access_token="token-chet"
        )
        await repo.mark_unusable(
            cu, status=ConnectionStatus.EXPIRED, reason="Token hết hạn"
        )

        settings = _settings()
        state = create_oauth_state(
            workspace_id=ws.id, user_id=owner.id, platform=Platform.FACEBOOK,
            settings=settings,
        )
        service = _service(db_session, monkeypatch, transport=_oauth_transport(),
                           settings=settings)
        await service.complete(platform=Platform.FACEBOOK, code="code", state=state)

        rows = await repo.list_for_workspace(ws.id)
        assert len(rows) == 1, "nối lại không được tạo bản ghi thứ hai"
        assert rows[0].status is ConnectionStatus.CONNECTED
        assert rows[0].failure_reason is None

    async def test_khong_co_page_nao_thi_bao_loi_ro_rang(self, db_session, monkeypatch):
        ws, owner = await _workspace_with_member(db_session)
        settings = _settings()
        state = create_oauth_state(
            workspace_id=ws.id, user_id=owner.id, platform=Platform.FACEBOOK,
            settings=settings,
        )
        service = _service(
            db_session, monkeypatch, transport=_oauth_transport(pages=[]), settings=settings
        )

        with pytest.raises(OAuthPermanentError, match="chưa quản lý Trang nào"):
            await service.complete(platform=Platform.FACEBOOK, code="code", state=state)

    async def test_page_thieu_token_thi_khong_noi(self, db_session, monkeypatch):
        """User bấm bỏ tích `pages_manage_posts`: Page hiện ra nhưng không kèm token.

        Nối vào lúc này thì UI chấm xanh mà mọi bài đều hỏng — phải chặn ngay.
        """
        ws, owner = await _workspace_with_member(db_session)
        settings = _settings()
        state = create_oauth_state(
            workspace_id=ws.id, user_id=owner.id, platform=Platform.FACEBOOK,
            settings=settings,
        )
        service = _service(
            db_session,
            monkeypatch,
            transport=_oauth_transport(pages=[{"id": "p1", "name": "Trang"}]),
            settings=settings,
        )

        with pytest.raises(OAuthPermanentError, match="chưa cấp quyền đăng bài"):
            await service.complete(platform=Platform.FACEBOOK, code="code", state=state)

    async def test_facebook_loi_5xx_la_loi_tam(self, db_session, monkeypatch):
        ws, owner = await _workspace_with_member(db_session)
        settings = _settings()
        state = create_oauth_state(
            workspace_id=ws.id, user_id=owner.id, platform=Platform.FACEBOOK,
            settings=settings,
        )
        transport = httpx.MockTransport(lambda r: httpx.Response(503, json={}))
        service = _service(db_session, monkeypatch, transport=transport, settings=settings)

        with pytest.raises(OAuthTemporaryError):
            await service.complete(platform=Platform.FACEBOOK, code="code", state=state)


class TestPickPage:
    def test_uu_tien_page_dang_bai_duoc(self):
        """Chủ tiệm hay được add vào Page người khác với vai trò chỉ-xem.

        Nối nhầm vào đó thì mọi bài đều hỏng, nên Page có CREATE_CONTENT thắng
        dù nó không đứng đầu danh sách.
        """
        pages = [
            {"id": "chi-xem", "name": "Page của bạn", "tasks": ["ANALYZE"]},
            {"id": "dang-duoc", "name": "Spa", "tasks": ["ANALYZE", "CREATE_CONTENT"]},
        ]
        assert _pick_page(pages)["id"] == "dang-duoc"

    def test_khong_page_nao_co_task_thi_lay_cai_dau(self):
        pages = [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}]
        assert _pick_page(pages)["id"] == "a"


class TestPlatformGuards:
    async def test_zalo_chua_co_adapter_thi_bao_chua_ho_tro(self, db_session, monkeypatch):
        ws, owner = await _workspace_with_member(db_session)
        service = _service(db_session, monkeypatch)

        with pytest.raises(PlatformNotSupported):
            service.start(
                workspace_id=ws.id, user_id=owner.id, platform=Platform.ZALO_OA
            )

    async def test_thieu_client_id_thi_khong_dua_user_sang_facebook(
        self, db_session, monkeypatch
    ):
        """Thiếu env là lỗi vận hành — chặn ở đây, đừng đẩy chủ tiệm sang trang lỗi."""
        ws, owner = await _workspace_with_member(db_session)
        service = _service(
            db_session, monkeypatch, settings=_settings(facebook_client_id="")
        )

        with pytest.raises(PlatformNotConfigured):
            service.start(
                workspace_id=ws.id, user_id=owner.id, platform=Platform.FACEBOOK
            )

    async def test_ngat_ket_noi_xoa_han_ca_token(self, db_session, monkeypatch):
        ws, _ = await _workspace_with_member(db_session)
        repo = ConnectionRepository(db_session)
        await repo.upsert(
            workspace_id=ws.id, platform=Platform.FACEBOOK, access_token=PAGE_TOKEN
        )
        service = _service(db_session, monkeypatch)

        await service.disconnect(workspace_id=ws.id, platform=Platform.FACEBOOK)

        assert await repo.get(workspace_id=ws.id, platform=Platform.FACEBOOK) is None

    async def test_ngat_kenh_chua_noi_bao_khong_tim_thay(self, db_session, monkeypatch):
        ws, _ = await _workspace_with_member(db_session)
        service = _service(db_session, monkeypatch)

        with pytest.raises(ConnectionNotFound):
            await service.disconnect(workspace_id=ws.id, platform=Platform.FACEBOOK)


# --- Adapter đăng bài --------------------------------------------------------


def _publisher(monkeypatch, handler) -> FacebookPublisher:
    import adapters.publishers.facebook as fb_module

    _patch_client(monkeypatch, httpx.MockTransport(handler), fb_module)
    return FacebookPublisher(_settings())


class TestFacebookPublish:
    async def test_bai_chi_chu_di_endpoint_feed(self, monkeypatch):
        seen: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["path"] = request.url.path
            seen["body"] = request.content.decode()
            return httpx.Response(200, json={"id": "page-1_post-9"})

        publisher = _publisher(monkeypatch, handler)
        result = await publisher.publish(
            PublishRequest(text="Ưu đãi gội đầu", external_account_id="page-1"),
            access_token=PAGE_TOKEN,
        )

        assert seen["path"].endswith("/page-1/feed")
        assert result.external_post_id == "page-1_post-9"
        # Token đi trong body, không trong query string (query nằm trong access log).
        assert "access_token" in seen["body"]

    async def test_bai_mot_anh_di_endpoint_photos_va_lay_post_id(self, monkeypatch):
        """/photos trả cả `id` (ảnh) và `post_id` (bài) — lấy nhầm thì tra không ra bài."""
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path.endswith("/page-1/photos")
            return httpx.Response(200, json={"id": "anh-1", "post_id": "page-1_post-7"})

        publisher = _publisher(monkeypatch, handler)
        result = await publisher.publish(
            PublishRequest(
                text="Ảnh tiệm", media_urls=["https://cdn/a.jpg"],
                external_account_id="page-1",
            ),
            access_token=PAGE_TOKEN,
        )

        assert result.external_post_id == "page-1_post-7"

    async def test_bai_nhieu_anh_upload_chua_publish_roi_moi_ghep(self, monkeypatch):
        """Ảnh phải `published=false`, nếu không sẽ thành nhiều bài rời rạc trên Trang."""
        calls: list[tuple[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = request.content.decode()
            calls.append((request.url.path, body))
            if request.url.path.endswith("/photos"):
                assert "published=false" in body
                return httpx.Response(200, json={"id": f"anh-{len(calls)}"})
            return httpx.Response(200, json={"id": "page-1_post-multi"})

        publisher = _publisher(monkeypatch, handler)
        result = await publisher.publish(
            PublishRequest(
                text="Album",
                media_urls=["https://cdn/a.jpg", "https://cdn/b.jpg"],
                external_account_id="page-1",
            ),
            access_token=PAGE_TOKEN,
        )

        assert len(calls) == 3, "hai ảnh + một bài"
        feed_body = calls[-1][1]
        assert "attached_media" in feed_body
        assert result.external_post_id == "page-1_post-multi"

    async def test_thieu_page_id_khong_retry(self, monkeypatch):
        publisher = _publisher(monkeypatch, lambda r: httpx.Response(200, json={}))

        with pytest.raises(ValidationPublishError):
            await publisher.publish(
                PublishRequest(text="x", external_account_id=None),
                access_token=PAGE_TOKEN,
            )

    async def test_2xx_thieu_post_id_thi_khong_retry(self, monkeypatch):
        """Bài có thể ĐÃ lên Trang — retry là đường thẳng tới đăng trùng.

        Đây là lựa chọn có chủ đích: thà vào dead-letter cho người đối soát còn
        hơn đăng bài thứ hai lên tường khách (lỗi không sửa được).
        """
        publisher = _publisher(monkeypatch, lambda r: httpx.Response(200, json={"ok": True}))

        with pytest.raises(ValidationPublishError, match="không trả mã bài đăng"):
            await publisher.publish(
                PublishRequest(text="x", external_account_id="page-1"),
                access_token=PAGE_TOKEN,
            )


class TestErrorClassification:
    """Map sai một mã lỗi = retry vô tận token chết, hoặc bỏ cuộc vì một 429."""

    @pytest.mark.parametrize("code", [190, 102, 10, 200])
    async def test_ma_loi_token_quyen_khong_retry(self, monkeypatch, code):
        publisher = _publisher(
            monkeypatch,
            lambda r: httpx.Response(
                400, json={"error": {"code": code, "message": "Token hỏng"}}
            ),
        )

        with pytest.raises(AuthPermissionError):
            await publisher.publish(
                PublishRequest(text="x", external_account_id="page-1"),
                access_token=PAGE_TOKEN,
            )

    @pytest.mark.parametrize("code", [4, 17, 32, 613, 1, 2])
    async def test_ma_loi_rate_limit_va_loi_tam_thi_retry(self, monkeypatch, code):
        publisher = _publisher(
            monkeypatch,
            lambda r: httpx.Response(
                400, json={"error": {"code": code, "message": "Quá giới hạn"}}
            ),
        )

        with pytest.raises(TemporaryPublishError):
            await publisher.publish(
                PublishRequest(text="x", external_account_id="page-1"),
                access_token=PAGE_TOKEN,
            )

    async def test_noi_dung_bi_tu_choi_khong_retry(self, monkeypatch):
        publisher = _publisher(
            monkeypatch,
            lambda r: httpx.Response(
                400, json={"error": {"code": 1500, "message": "URL ảnh không hợp lệ"}}
            ),
        )

        with pytest.raises(ValidationPublishError):
            await publisher.publish(
                PublishRequest(text="x", external_account_id="page-1"),
                access_token=PAGE_TOKEN,
            )

    async def test_5xx_khong_co_ma_loi_van_la_loi_tam(self, monkeypatch):
        publisher = _publisher(monkeypatch, lambda r: httpx.Response(502, text="bad gateway"))

        with pytest.raises(TemporaryPublishError):
            await publisher.publish(
                PublishRequest(text="x", external_account_id="page-1"),
                access_token=PAGE_TOKEN,
            )

    async def test_timeout_la_loi_tam(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("hết giờ", request=request)

        publisher = _publisher(monkeypatch, handler)

        with pytest.raises(TemporaryPublishError):
            await publisher.publish(
                PublishRequest(text="x", external_account_id="page-1"),
                access_token=PAGE_TOKEN,
            )


class TestTokenRedaction:
    """Token không được lọt vào message lỗi.

    `PublishError.detail` được ghi thẳng vào `publish_jobs.failure_detail` và
    vào log. Một lần rơi về `response.text` thô là token nằm trong DB dưới dạng
    chữ thường — Graph có vọng lại tham số đã gửi trong body lỗi.
    """

    async def test_body_loi_vong_lai_token_khong_lot_vao_detail(self, monkeypatch):
        # Body lỗi mô phỏng đúng kiểu Graph vọng lại tham số đã nhận.
        body = {
            "error": {
                "code": 1500,
                "message": "Tham số không hợp lệ",
                "error_data": {"gui_len": f"access_token={PAGE_TOKEN}"},
            }
        }
        publisher = _publisher(monkeypatch, lambda r: httpx.Response(400, json=body))

        with pytest.raises(ValidationPublishError) as exc_info:
            await publisher.publish(
                PublishRequest(text="x", external_account_id="page-1"),
                access_token=PAGE_TOKEN,
            )

        assert PAGE_TOKEN not in str(exc_info.value)
        assert PAGE_TOKEN not in exc_info.value.detail

    async def test_body_loi_khong_phai_json_khong_lam_lo_token(self, monkeypatch):
        """Không có `error.message` thì KHÔNG được rơi về `response.text`."""
        publisher = _publisher(
            monkeypatch,
            lambda r: httpx.Response(400, text=f"Loi: access_token={PAGE_TOKEN} sai"),
        )

        with pytest.raises(ValidationPublishError) as exc_info:
            await publisher.publish(
                PublishRequest(text="x", external_account_id="page-1"),
                access_token=PAGE_TOKEN,
            )

        assert PAGE_TOKEN not in exc_info.value.detail

    async def test_loi_oauth_khong_lam_lo_client_secret(self, monkeypatch):
        import adapters.oauth.facebook as fb_module

        transport = httpx.MockTransport(
            lambda r: httpx.Response(400, text="secret=secret-456 sai")
        )
        _patch_client(monkeypatch, transport, fb_module)
        client = FacebookOAuthClient(_settings())

        with pytest.raises(OAuthPermanentError) as exc_info:
            await client.exchange_code("code")

        assert "secret-456" not in exc_info.value.detail

    def test_repr_cua_oauth_account_che_token(self):
        """`logger.exception` in cả local variable của frame — repr phải sạch sẵn."""
        from adapters.oauth.base import OAuthAccount

        account = OAuthAccount(
            external_account_id="page-1", account_name="Spa", access_token=PAGE_TOKEN
        )
        assert PAGE_TOKEN not in repr(account)
        assert "***" in repr(account)


async def test_facebook_data_deletion_callback():
    """Endpoint /connections/facebook/data-deletion trả JSON url &
    confirmation_code đúng chuẩn Meta."""
    from httpx import ASGITransport, AsyncClient

    from api.main import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/connections/facebook/data-deletion")
        assert res.status_code == 200
        data = res.json()
        assert "url" in data
        assert "confirmation_code" in data
        assert data["confirmation_code"].startswith("del_")
        # Route chuẩn sau khi đổi tên sang tiếng Anh. `/huong-dan-xoa-du-lieu`
        # vẫn sống nhờ alias trong `apps/web/src/middleware.ts`, nhưng URL Havi
        # tự sinh ra thì phải trỏ vào đường chính thức.
        assert "/data-deletion" in data["url"]


