"""Dependency dùng chung: auth context, workspace scope, và service injection.

Mọi endpoint (trừ /health và /auth/*) yêu cầu `Authorization: Bearer <JWT>` và bị
scope theo `active_workspace_id` — không cho leak chéo tenant.
"""

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.db import DbSessionDep
from adapters.persistence.otp_repository import OtpRepository
from adapters.persistence.refresh_session_repository import RefreshSessionRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.auth_service import AuthService
from application.services.brand_profile_service import BrandProfileService
from application.services.workspace_service import WorkspaceService
from core.config import Settings, get_settings
from core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=True)

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_auth_service(session: DbSessionDep, settings: SettingsDep) -> AuthService:
    return AuthService(
        users=UserRepository(session),
        otp_challenges=OtpRepository(session),
        refresh_sessions=RefreshSessionRepository(session),
        settings=settings,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_workspace_service(
    session: DbSessionDep, auth_service: AuthServiceDep
) -> WorkspaceService:
    return WorkspaceService(
        workspaces=WorkspaceRepository(session),
        members=WorkspaceMemberRepository(session),
        users=UserRepository(session),
        auth_service=auth_service,
    )


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def get_brand_profile_service(session: DbSessionDep) -> BrandProfileService:
    return BrandProfileService(
        profiles=BrandProfileRepository(session),
        workspaces=WorkspaceRepository(session),
    )


BrandProfileServiceDep = Annotated[BrandProfileService, Depends(get_brand_profile_service)]


class AuthContext:
    """Thông tin giải mã từ JWT."""

    def __init__(self, user_id: UUID, active_workspace_id: UUID | None) -> None:
        self.user_id = user_id
        self.active_workspace_id = active_workspace_id


async def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    settings: SettingsDep,
    session: DbSessionDep,
) -> AuthContext:
    try:
        decoded = decode_access_token(credentials.credentials, settings)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if decoded.active_workspace_id is not None:
        members = WorkspaceMemberRepository(session)
        is_member = await members.is_member(
            workspace_id=decoded.active_workspace_id, user_id=decoded.user_id
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Không còn là thành viên của workspace này",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return AuthContext(user_id=decoded.user_id, active_workspace_id=decoded.active_workspace_id)


AuthDep = Annotated[AuthContext, Depends(get_auth_context)]


def get_workspace_id(auth: AuthDep) -> UUID:
    if auth.active_workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tài khoản chưa chọn workspace — hoàn thành onboarding trước",
        )
    return auth.active_workspace_id


WorkspaceDep = Annotated[UUID, Depends(get_workspace_id)]


async def require_path_workspace_member(
    workspace_id: UUID, auth: AuthDep, session: DbSessionDep
) -> UUID:
    """Cho route có `{workspace_id}` trong path (get/update/members/...) — khác
    `WorkspaceDep` (đọc từ JWT). Không có check này thì bất kỳ JWT hợp lệ nào
    cũng đọc/sửa được workspace của người khác miễn biết UUID — đây là chặn
    cross-tenant leak thật, không chỉ ở active_workspace_id.
    """
    members = WorkspaceMemberRepository(session)
    if not await members.is_member(workspace_id=workspace_id, user_id=auth.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập workspace này",
        )
    return workspace_id


PathWorkspaceMemberDep = Annotated[UUID, Depends(require_path_workspace_member)]
