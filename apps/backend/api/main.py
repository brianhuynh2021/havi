"""Havi API — FastAPI app factory.

Chạy local:
    uv run uvicorn api.main:app --reload --port 8000

OpenAPI contract cho frontend: http://localhost:8000/openapi.json
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in ROUTERS:
        app.include_router(router)

    return app


app = create_app()
