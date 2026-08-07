"""Use case cho /workspaces/* — tạo tiệm, chọn tiệm, quản lý thành viên.

Ném exception thuần, router dịch sang HTTP status — cùng quy ước với auth_service.py.
"""

from dataclasses import dataclass
from uuid import UUID

from adapters.persistence.user_repository import UserRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.auth_service import AuthService, TokenPairResult
from core.enums import Industry, PublishMode, WorkspaceRole
from core.phone import InvalidPhoneNumber, normalize_vietnamese_phone
from domain.models.user import User
from domain.models.workspace import Workspace, WorkspaceMember


class WorkspaceNotFound(Exception):
    pass


class InviteUserNotFound(Exception):
    pass


class AlreadyMember(Exception):
    pass


class CannotRemoveLastOwner(Exception):
    pass


@dataclass
class MemberWithUser:
    member: WorkspaceMember
    user: User


class WorkspaceService:
    def __init__(
        self,
        *,
        workspaces: WorkspaceRepository,
        members: WorkspaceMemberRepository,
        users: UserRepository,
        auth_service: AuthService,
    ) -> None:
        self._workspaces = workspaces
        self._members = members
        self._users = users
        self._auth_service = auth_service

    async def list_workspaces(self, user_id: UUID) -> list[Workspace]:
        return await self._workspaces.list_for_user(user_id)

    async def create_workspace(
        self, *, owner_user_id: UUID, name: str, industry: Industry
    ) -> Workspace:
        """Bước 1 Onboarding. Tự đặt làm active_workspace_id — client gọi lại
        `/auth/refresh` (hoặc `/workspaces/{id}/activate`) để JWT phản ánh workspace mới.
        """
        workspace = await self._workspaces.create(
            name=name, industry=industry, owner_user_id=owner_user_id
        )
        await self._members.add(
            workspace_id=workspace.id, user_id=owner_user_id, role=WorkspaceRole.OWNER
        )
        owner = await self._users.get_by_id(owner_user_id)
        if owner is not None:
            await self._users.set_active_workspace(owner, workspace.id)
        return workspace

    async def get_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFound()
        return workspace

    async def update_workspace(
        self,
        workspace_id: UUID,
        *,
        name: str | None,
        industry: Industry | None,
        publish_mode: PublishMode | None,
    ) -> Workspace:
        workspace = await self.get_workspace(workspace_id)
        return await self._workspaces.update(
            workspace, name=name, industry=industry, publish_mode=publish_mode
        )

    async def activate_workspace(self, *, user_id: UUID, workspace_id: UUID) -> TokenPairResult:
        """Membership đã được xác nhận ở dependency router — chỉ set + reissue token."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise WorkspaceNotFound()
        await self._users.set_active_workspace(user, workspace_id)
        return await self._auth_service.issue_token_pair(user)

    async def list_members(self, workspace_id: UUID) -> list[MemberWithUser]:
        rows = await self._members.list_with_user_for_workspace(workspace_id)
        return [MemberWithUser(member=member, user=user) for member, user in rows]

    async def invite_member(
        self, *, workspace_id: UUID, phone: str, role: WorkspaceRole
    ) -> MemberWithUser:
        try:
            normalized = normalize_vietnamese_phone(phone)
        except InvalidPhoneNumber as exc:
            raise InviteUserNotFound() from exc

        user = await self._users.get_by_phone(normalized)
        if user is None:
            raise InviteUserNotFound()
        if await self._members.is_member(workspace_id=workspace_id, user_id=user.id):
            raise AlreadyMember()

        member = await self._members.add(workspace_id=workspace_id, user_id=user.id, role=role)
        return MemberWithUser(member=member, user=user)

    async def remove_member(self, *, workspace_id: UUID, user_id: UUID) -> None:
        member = await self._members.get(workspace_id=workspace_id, user_id=user_id)
        if member is None:
            return  # đã không phải thành viên — idempotent
        if member.role == WorkspaceRole.OWNER:
            owner_count = await self._members.count_owners(workspace_id)
            if owner_count <= 1:
                raise CannotRemoveLastOwner()
        await self._members.remove(member)
