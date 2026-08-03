"""/workspaces/* — multi-tenant. 1 user có thể thuộc nhiều workspace.

Nếu user có >1 workspace, frontend hiện màn "Chọn tiệm" sau login.
"""

from uuid import UUID

from fastapi import APIRouter, status

from api.deps import AuthDep
from api.errors import NotImplementedEndpoint
from core.schemas import (
    TokenPair,
    Workspace,
    WorkspaceCreate,
    WorkspaceMember,
    WorkspaceMemberInvite,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[Workspace])
def list_workspaces(auth: AuthDep) -> list[Workspace]:
    del auth
    raise NotImplementedEndpoint()


@router.post("", response_model=Workspace, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, auth: AuthDep) -> Workspace:
    """Bước 1 Onboarding: chọn ngành rồi tạo tiệm."""
    del payload, auth
    raise NotImplementedEndpoint()


@router.get("/{workspace_id}", response_model=Workspace)
def get_workspace(workspace_id: UUID, auth: AuthDep) -> Workspace:
    del workspace_id, auth
    raise NotImplementedEndpoint()


@router.patch("/{workspace_id}", response_model=Workspace)
def update_workspace(workspace_id: UUID, payload: WorkspaceUpdate, auth: AuthDep) -> Workspace:
    """Đổi tên, ngành, hoặc toggle "Chế độ đăng bài" (review_first | full_auto)."""
    del workspace_id, payload, auth
    raise NotImplementedEndpoint()


@router.post("/{workspace_id}/activate", response_model=TokenPair)
def activate_workspace(workspace_id: UUID, auth: AuthDep) -> TokenPair:
    """Đổi `active_workspace_id` trong JWT — màn "Chọn tiệm"."""
    del workspace_id, auth
    raise NotImplementedEndpoint()


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMember])
def list_members(workspace_id: UUID, auth: AuthDep) -> list[WorkspaceMember]:
    del workspace_id, auth
    raise NotImplementedEndpoint()


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMember,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    workspace_id: UUID, payload: WorkspaceMemberInvite, auth: AuthDep
) -> WorkspaceMember:
    del workspace_id, payload, auth
    raise NotImplementedEndpoint()


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(workspace_id: UUID, user_id: UUID, auth: AuthDep) -> None:
    del workspace_id, user_id, auth
    raise NotImplementedEndpoint()
