"""Use case cho /workspaces/* — tạo tiệm, chọn tiệm, quản lý thành viên.

Ném exception thuần, router dịch sang HTTP status — cùng quy ước với auth_service.py.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.auth_service import AuthService, TokenPairResult
from core.enums import Industry, WorkspaceRole
from core.events import EventLogEntry
from domain.models.user import User
from domain.models.workspace import Workspace, WorkspaceMember
from domain.policies import plan_limits

if TYPE_CHECKING:
    from application.services.media_service import MediaService


class WorkspaceNotFound(Exception):
    pass


class InviteUserNotFound(Exception):
    pass


class AlreadyMember(Exception):
    pass


class CannotRemoveLastOwner(Exception):
    pass


class CannotDeleteWorkspaceNotOwner(Exception):
    pass


@dataclass
class MemberWithUser:
    member: WorkspaceMember
    user: User


class NotOrganizationMember(Exception):
    """Tạo thương hiệu trong một tổ chức mình không thuộc về."""


class WorkspaceService:
    def __init__(
        self,
        *,
        workspaces: WorkspaceRepository,
        members: WorkspaceMemberRepository,
        organizations=None,  # noqa: ANN001 — OrganizationRepository, tránh vòng import
        users: UserRepository,
        auth_service: AuthService,
        events: EventLogRepository | None = None,
        media_service: "MediaService | None" = None,
    ) -> None:
        self._workspaces = workspaces
        self._members = members
        self._organizations = organizations
        self._users = users
        self._auth_service = auth_service
        self._events = events
        self._media_service = media_service

    async def list_workspaces(self, user_id: UUID) -> list[Workspace]:
        return await self._workspaces.list_for_user(user_id)

    async def create_workspace(
        self,
        *,
        owner_user_id: UUID,
        name: str,
        industry: Industry,
        organization_id: UUID | None = None,
    ) -> Workspace:
        """Bước 1 Onboarding. Tự đặt làm active_workspace_id — client gọi lại
        `/auth/refresh` (hoặc `/workspaces/{id}/activate`) để JWT phản ánh workspace mới.
        """
        # Mỗi workspace thuộc về một tổ chức. Không truyền vào thì dùng tổ chức
        # đầu tiên của người tạo, tạo mới nếu họ chưa có — chủ tiệm đơn lẻ không
        # bao giờ thấy khái niệm này, nhưng ngày họ mở thương hiệu thứ hai thì
        # không phải migrate gì.
        if organization_id is None and self._organizations is not None:
            organization_id = await self._organizations.ensure_personal_org(
                user_id=owner_user_id, name=name
            )
        elif organization_id is not None and self._organizations is not None:
            # Tạo thương hiệu trong một tổ chức có sẵn: người tạo phải là thành
            # viên tổ chức đó, nếu không họ vừa gắn dữ liệu vào công ty người khác.
            if await self._organizations.get_role(
                organization_id=organization_id, user_id=owner_user_id
            ) is None:
                raise NotOrganizationMember()

        workspace = await self._workspaces.create(
            name=name,
            industry=industry,
            owner_user_id=owner_user_id,
            organization_id=organization_id,
        )
        await self._members.add(
            workspace_id=workspace.id, user_id=owner_user_id, role=WorkspaceRole.OWNER
        )
        owner = await self._users.get_by_id(owner_user_id)
        if owner is not None:
            await self._users.set_active_workspace(owner, workspace.id)

        if self._events is not None:
            await self._events.record(
                EventLogEntry(
                    workspace_id=workspace.id,
                    job_kind="consent.workspace_created",
                    input_summary=f"user_id={owner_user_id} name={name} industry={industry.value}",
                )
            )
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
    ) -> Workspace:
        workspace = await self.get_workspace(workspace_id)
        updated = await self._workspaces.update(
            workspace, name=name, industry=industry
        )
        return updated

    async def delete_workspace(self, *, workspace_id: UUID, user_id: UUID) -> None:
        workspace = await self.get_workspace(workspace_id)
        member = await self._members.get(workspace_id=workspace_id, user_id=user_id)
        if member is None or member.role != WorkspaceRole.OWNER:
            raise CannotDeleteWorkspaceNotOwner()

        if self._events is not None:
            await self._events.record(
                EventLogEntry(
                    workspace_id=workspace_id,
                    job_kind="consent.workspace_deleted",
                    input_summary=f"user_id={user_id} workspace_name={workspace.name}",
                )
            )

        if self._media_service is not None:
            assets, _ = await self._media_service.list_media(
                workspace_id=workspace_id,
                type=None,
                status=None,
                tag=None,
                limit=1000,
                offset=0,
            )
            for asset in assets:
                try:
                    await self._media_service._storage.delete_object(asset.object_key)
                except Exception:
                    pass

        await self._workspaces.delete_workspace_cascade(workspace_id)

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
        self, *, workspace_id: UUID, email: str, role: WorkspaceRole
    ) -> MemberWithUser:
        user = await self._users.get_by_email(email.strip().lower())
        if user is None:
            raise InviteUserNotFound()
        if await self._members.is_member(workspace_id=workspace_id, user_id=user.id):
            raise AlreadyMember()

        # Trần ghế theo gói. Kiểm **sau** `AlreadyMember`: mời lại người đã ở
        # trong workspace không thêm ghế nào, nên báo "hết ghế" ở đó là nói sai
        # nguyên nhân và đẩy người dùng đi nâng gói mà không cần.
        workspace = await self._workspaces.get(workspace_id)
        if workspace is not None:
            plan_limits.check_seats(
                plan=workspace.plan,
                current=await self._members.count_members(workspace_id),
                extra_seats=workspace.extra_seats,
            )

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

    async def update_member_role(
        self, *, workspace_id: UUID, user_id: UUID, role: WorkspaceRole
    ) -> MemberWithUser:
        member = await self._members.get(workspace_id=workspace_id, user_id=user_id)
        if member is None:
            raise InviteUserNotFound()

        if member.role == WorkspaceRole.OWNER and role != WorkspaceRole.OWNER:
            owner_count = await self._members.count_owners(workspace_id)
            if owner_count <= 1:
                raise CannotRemoveLastOwner()

        member = await self._members.update(member, role=role)
        user = await self._users.get_by_id(user_id)
        # user cannot be None if member exists
        return MemberWithUser(member=member, user=user)  # type: ignore

    async def resend_invite(
        self, *, workspace_id: UUID, user_id: UUID
    ) -> MemberWithUser:
        member = await self._members.get(workspace_id=workspace_id, user_id=user_id)
        if member is None:
            raise InviteUserNotFound()
        
        user = await self._users.get_by_id(user_id)
        # Hiện tại Havi tự động thêm vào workspace luôn nên resend_invite chỉ là 
        # mock endpoint để sau này có thể gắn EmailSender vào gửi email thật.
        return MemberWithUser(member=member, user=user)  # type: ignore
