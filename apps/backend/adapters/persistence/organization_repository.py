"""Repository cho Organization — tầng doanh nghiệp phía trên workspace."""

import uuid
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import OrganizationRole
from domain.models.organization import Organization, OrganizationMember
from domain.models.workspace import Workspace


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str, owner_user_id: UUID) -> Organization:
        org = Organization(name=name, owner_user_id=owner_user_id)
        self._session.add(org)
        await self._session.flush()
        await self.add_member(
            organization_id=org.id, user_id=owner_user_id, role=OrganizationRole.OWNER
        )
        return org

    async def add_member(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        role: OrganizationRole = OrganizationRole.MEMBER,
    ) -> None:
        """Thêm người vào tổ chức. Gọi lại với cùng cặp id thì không lỗi.

        `ON CONFLICT DO NOTHING` chứ không check-trước-insert: onboarding và lời
        mời có thể chạy song song, và cả hai cùng thấy "chưa có" rồi cùng insert.
        """
        await self._session.execute(
            insert(OrganizationMember)
            .values(organization_id=organization_id, user_id=user_id, role=role)
            .on_conflict_do_nothing()
        )

    async def get_for_user(self, user_id: UUID) -> list[Organization]:
        """Các tổ chức người này thuộc về."""
        result = await self._session.execute(
            select(Organization)
            .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
            .where(OrganizationMember.user_id == user_id)
            .order_by(Organization.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_role(self, *, organization_id: UUID, user_id: UUID) -> OrganizationRole | None:
        """`None` = không thuộc tổ chức này. Caller phải fail-closed trên `None`."""
        result = await self._session.execute(
            select(OrganizationMember.role).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def workspaces_of(self, organization_id: UUID) -> list[Workspace]:
        """Các thương hiệu / chi nhánh thuộc tổ chức, cũ trước mới sau."""
        result = await self._session.execute(
            select(Workspace)
            .where(Workspace.organization_id == organization_id)
            .order_by(Workspace.created_at.asc())
        )
        return list(result.scalars().all())

    async def ensure_personal_org(self, *, user_id: UUID, name: str) -> uuid.UUID:
        """Tổ chức đầu tiên của một người — tạo nếu chưa có, trả id.

        Chủ tiệm đơn lẻ không bao giờ thấy khái niệm "tổ chức". Nhưng workspace
        đầu tiên của họ vẫn phải thuộc về một tổ chức, để ngày họ mở thương hiệu
        thứ hai thì không phải migrate gì.
        """
        existing = await self.get_for_user(user_id)
        if existing:
            return existing[0].id
        org = await self.create(name=name, owner_user_id=user_id)
        return org.id

    async def delete_empty_owned_organizations(self, user_id: UUID) -> None:
        """Xoá tổ chức cá nhân không còn workspace trước khi xoá tài khoản.

        Workspace được xoá trước theo luật sở hữu. Giữ lại một organization rỗng
        vừa vô nghĩa vừa giữ FK tới user, khiến quyền xoá tài khoản không thể
        hoàn tất.
        """
        owned = list(
            (
                await self._session.execute(
                    select(Organization.id).where(Organization.owner_user_id == user_id)
                )
            ).scalars()
        )
        for organization_id in owned:
            workspace_count = await self._session.scalar(
                select(func.count(Workspace.id)).where(
                    Workspace.organization_id == organization_id
                )
            )
            if workspace_count:
                continue
            await self._session.execute(
                delete(OrganizationMember).where(
                    OrganizationMember.organization_id == organization_id
                )
            )
            await self._session.execute(
                delete(Organization).where(Organization.id == organization_id)
            )

        await self._session.execute(
            delete(OrganizationMember).where(OrganizationMember.user_id == user_id)
        )
        await self._session.flush()
