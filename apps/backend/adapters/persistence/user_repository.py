from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_phone(self, phone: str) -> User | None:
        result = await self._session.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, *, phone: str, name: str) -> User:
        user = User(phone=phone, name=name)
        self._session.add(user)
        await self._session.flush()
        return user

    async def set_active_workspace(self, user: User, workspace_id: UUID) -> None:
        user.active_workspace_id = workspace_id
        await self._session.flush()
