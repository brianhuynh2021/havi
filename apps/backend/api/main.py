"""Havi API — FastAPI app factory.

Chạy local:
    uv run uvicorn api.main:app --reload --port 8000

OpenAPI contract cho frontend: http://localhost:8000/openapi.json
"""

import logging
import secrets
import time
from html import escape

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse

from api.routers import (
    analytics,
    auth,
    billing,
    brand_profile,
    calendar,
    connections,
    content,
    health,
    inbox,
    leads,
    media,
    workspaces,
)
from core.config import get_settings
from core.request_context import (
    REQUEST_ID_HEADER,
    reset_request_id,
    sanitize_request_id,
    set_request_id,
)
from core.structured_logging import log_json

logger = logging.getLogger("havi.http")

DESCRIPTION = """
Backend của Havi — sở hữu database, secret, prompt production và approval state machine.

Nguyên tắc bất di bất dịch:
- Mặc định không nội dung nào lên mạng khi chủ chưa duyệt (`review_first`).
- Reply cho khách không bao giờ có `full_auto`, trừ FAQ chủ đã duyệt sẵn từng câu.
- Token nền tảng mã hoá bằng `TOKEN_ENCRYPTION_KEY`, chỉ backend giải mã.
"""

ROUTERS = (
    health.router,
    auth.router,
    workspaces.router,
    brand_profile.router,
    media.router,
    content.router,
    calendar.router,
    connections.router,
    inbox.router,
    leads.router,
    analytics.router,
    billing.router,
)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Havi API",
        version="0.1.0",
        description=DESCRIPTION,
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
    )

    cors_origins = list(
        set(
            settings.cors_origins
            + [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://0.0.0.0:3000",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ]
        )
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"https?://.*" if settings.debug else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request, call_next):  # noqa: ANN001
        request_id = sanitize_request_id(request.headers.get(REQUEST_ID_HEADER))
        started = time.perf_counter()
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000)
            log_json(
                logger,
                logging.ERROR,
                "http.request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
            )
            raise
        finally:
            reset_request_id(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        duration_ms = round((time.perf_counter() - started) * 1000)
        log_json(
            logger,
            logging.INFO,
            "http.request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    for router in ROUTERS:
        app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root_handler() -> HTMLResponse:
        """Trang gốc — chỉ để Zalo xác minh domain, không phải endpoint dữ liệu.

        Thẻ meta chỉ xuất hiện khi `HAVI_ZALO_SITE_VERIFICATION` được đặt, và mã
        được escape trước khi ghép vào HTML.
        """
        verification = settings.zalo_site_verification
        meta = ""
        if verification:
            content = escape(verification, quote=True)
            meta = f'<meta name="zalo-platform-site-verification" content="{content}" />'
        return HTMLResponse(
            f"<!DOCTYPE html><html><head>{meta}</head><body>Havi Backend API</body></html>"
        )

    @app.get("/zalo_verifier{suffix}", include_in_schema=False)
    async def zalo_verifier_handler(suffix: str) -> PlainTextResponse:
        """File xác minh domain của Zalo.

        So khớp tuyệt đối `suffix` với cấu hình rồi trả nội dung dựng sẵn. Không
        đọc file theo input của request: `{suffix}` không nuốt dấu `/`, và không
        có `os.path.join` nào ở đây, nên không tồn tại đường traversal.
        """
        expected = settings.zalo_verifier_suffix
        if not expected or not secrets.compare_digest(suffix, expected):
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return PlainTextResponse(
            f"zalo-platform-site-verification={settings.zalo_site_verification}"
        )

    return app


app = create_app()
