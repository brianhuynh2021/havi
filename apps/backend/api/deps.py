"""Dependency dùng chung: auth context và workspace scope.

Mọi endpoint (trừ /health và /auth/*) yêu cầu `Authorization: Bearer <JWT>` và bị
scope theo `active_workspace_id` — không cho leak chéo tenant.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=True)

SettingsDep = Annotated[Settings, Depends(get_settings)]


class AuthContext:
    """Thông tin giải mã từ JWT."""

    def __init__(self, user_id: UUID, active_workspace_id: UUID) -> None:
        self.user_id = user_id
        self.active_workspace_id = active_workspace_id


def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    settings: SettingsDep,
) -> AuthContext:
    # TODO(auth): giải mã JWT bằng settings.jwt_secret, lấy sub + active_workspace_id,
    # kiểm tra user còn là thành viên của workspace đó.
    del settings
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Xác thực JWT chưa được implement",
        headers={"WWW-Authenticate": "Bearer"},
    )


AuthDep = Annotated[AuthContext, Depends(get_auth_context)]


def get_workspace_id(auth: AuthDep) -> UUID:
    return auth.active_workspace_id


WorkspaceDep = Annotated[UUID, Depends(get_workspace_id)]
