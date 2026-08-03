"""/connections/* — OAuth nền tảng.

Access/refresh token mã hoá bằng `TOKEN_ENCRYPTION_KEY` và KHÔNG BAO GIỜ nằm trong
response. Không được publish khi `status != connected`.
"""

from fastapi import APIRouter, status

from api.deps import AuthDep, WorkspaceDep
from api.errors import NotImplementedEndpoint
from core.enums import Platform
from core.schemas import OAuthStartResponse, PlatformConnection

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_model=list[PlatformConnection])
def list_connections(workspace_id: WorkspaceDep) -> list[PlatformConnection]:
    """Bước 2 Onboarding + trang Cài đặt: chấm xanh/đỏ theo `status`."""
    del workspace_id
    raise NotImplementedEndpoint()


@router.post("/{platform}/start", response_model=OAuthStartResponse)
def start_oauth(platform: Platform, auth: AuthDep) -> OAuthStartResponse:
    del platform, auth
    raise NotImplementedEndpoint()


@router.get("/{platform}/callback", response_model=PlatformConnection)
def oauth_callback(platform: Platform, code: str, state: str) -> PlatformConnection:
    del platform, code, state
    raise NotImplementedEndpoint()


@router.delete("/{platform}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(platform: Platform, auth: AuthDep) -> None:
    del platform, auth
    raise NotImplementedEndpoint()
