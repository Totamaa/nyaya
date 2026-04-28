from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.model import UserModel


class UserRepository:

    async def get_by_id(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        return result.scalars().one_or_none()

    async def get_by_external_id(
        self,
        external_id: str,
        db: AsyncSession,
    ) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.external_id == external_id)
        result = await db.execute(stmt)
        return result.scalars().one_or_none()

    async def create(
        self,
        user: UserModel,
        db: AsyncSession,
    ) -> UserModel:
        db.add(user)
        await db.flush()
        return user
