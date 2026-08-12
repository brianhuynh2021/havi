"""/workspaces/* — multi-tenant. 1 user có thể thuộc nhiều workspace.

Nếu user có >1 workspace, frontend hiện màn "Chọn tiệm" sau login.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from api.deps import AuthDep, PathWorkspaceMemberDep, WorkspaceServiceDep
from application.services.workspace_service import (
    AlreadyMember,
    CannotDeleteWorkspaceNotOwner,
    CannotRemoveLastOwner,
    InviteUserNotFound,
    WorkspaceNotFound,
)
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
async def list_workspaces(
    auth: AuthDep, workspace_service: WorkspaceServiceDep
) -> list[Workspace]:
    workspaces = await workspace_service.list_workspaces(auth.user_id)
    return [Workspace.model_validate(w) for w in workspaces]


@router.post("", response_model=Workspace, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate, auth: AuthDep, workspace_service: WorkspaceServiceDep
) -> Workspace:
    """Bước 1 Onboarding: chọn ngành rồi tạo tiệm.

    Tự set làm `active_workspace_id` — JWT hiện tại của client chưa phản ánh
    điều này, gọi `/auth/refresh` (hoặc `/workspaces/{id}/activate`) ngay sau
    để lấy token mới.
    """
    workspace = await workspace_service.create_workspace(
        owner_user_id=auth.user_id, name=payload.name, industry=payload.industry
    )
    return Workspace.model_validate(workspace)


@router.get("/{workspace_id}", response_model=Workspace)
async def get_workspace(
    workspace_id: PathWorkspaceMemberDep, workspace_service: WorkspaceServiceDep
) -> Workspace:
    try:
        workspace = await workspace_service.get_workspace(workspace_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy workspace") from exc
    return Workspace.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=Workspace)
async def update_workspace(
    workspace_id: PathWorkspaceMemberDep,
    payload: WorkspaceUpdate,
    workspace_service: WorkspaceServiceDep,
) -> Workspace:
    """Đổi tên, ngành, hoặc toggle "Chế độ đăng bài" (review_first | full_auto)."""
    try:
        workspace = await workspace_service.update_workspace(
            workspace_id,
            name=payload.name,
            industry=payload.industry,
            publish_mode=payload.publish_mode,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy workspace") from exc
    return Workspace.model_validate(workspace)


@router.post("/{workspace_id}/activate", response_model=TokenPair)
async def activate_workspace(
    workspace_id: PathWorkspaceMemberDep, auth: AuthDep, workspace_service: WorkspaceServiceDep
) -> TokenPair:
    """Đổi `active_workspace_id` trong JWT — màn "Chọn tiệm"."""
    result = await workspace_service.activate_workspace(
        user_id=auth.user_id, workspace_id=workspace_id
    )
    return TokenPair(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        active_workspace_id=result.active_workspace_id,
        needs_onboarding=result.needs_onboarding,
    )


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMember])
async def list_members(
    workspace_id: PathWorkspaceMemberDep, workspace_service: WorkspaceServiceDep
) -> list[WorkspaceMember]:
    rows = await workspace_service.list_members(workspace_id)
    return [
        WorkspaceMember(user_id=row.user.id, name=row.user.name, role=row.member.role)
        for row in rows
    ]


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMember,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    workspace_id: PathWorkspaceMemberDep,
    payload: WorkspaceMemberInvite,
    workspace_service: WorkspaceServiceDep,
) -> WorkspaceMember:
    try:
        row = await workspace_service.invite_member(
            workspace_id=workspace_id, email=payload.email, role=payload.role
        )
    except InviteUserNotFound as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Email chưa có tài khoản Havi — mời họ đăng ký trước",
        ) from exc
    except AlreadyMember as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Đã là thành viên workspace này") from exc
    return WorkspaceMember(user_id=row.user.id, name=row.user.name, role=row.member.role)


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: PathWorkspaceMemberDep,
    user_id: UUID,
    workspace_service: WorkspaceServiceDep,
) -> None:
    try:
        await workspace_service.remove_member(workspace_id=workspace_id, user_id=user_id)
    except CannotRemoveLastOwner as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Không thể xoá owner duy nhất của workspace"
        ) from exc


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: PathWorkspaceMemberDep,
    auth: AuthDep,
    workspace_service: WorkspaceServiceDep,
) -> None:
    """Xoá workspace và toàn bộ dữ liệu thuộc về workspace (owner only)."""
    try:
        await workspace_service.delete_workspace(workspace_id=workspace_id, user_id=auth.user_id)
    except CannotDeleteWorkspaceNotOwner as exc:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Chỉ owner mới có quyền xoá workspace"
        ) from exc

