from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> User | None:
        result = await self._session.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, *, email: str, name: str, password_hash: str) -> User:
        user = User(email=email, name=name, password_hash=password_hash)
        self._session.add(user)
        await self._session.flush()
        return user

    async def set_password_hash(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        await self._session.flush()

    async def set_phone(self, user: User, phone: str) -> None:
        user.phone = phone
        await self._session.flush()

    async def set_active_workspace(self, user: User, workspace_id: UUID | None) -> None:
        user.active_workspace_id = workspace_id
        await self._session.flush()

    async def delete(self, user: User) -> None:
        await self._session.delete(user)
        await self._session.flush()

