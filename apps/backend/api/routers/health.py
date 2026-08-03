"""Health check — endpoint duy nhất không cần JWT, dùng cho probe khi deploy."""

from fastapi import APIRouter

from api.deps import SettingsDep
from core.schemas import HaviModel

router = APIRouter(tags=["health"])


class HealthResponse(HaviModel):
    status: str
    env: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(status="ok", env=settings.env, version="0.1.0")
