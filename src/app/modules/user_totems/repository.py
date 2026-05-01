import uuid
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user_totems.model import UserTotemModel


class UserTotemRepository:

    async def get_by_user_month(
        self,
        user_id: UUID,
        month: date,
        db: AsyncSession,
    ) -> list[UserTotemModel]:
        stmt = (
            select(UserTotemModel)
            .where(UserTotemModel.user_id == user_id, UserTotemModel.month == month)
            .options(selectinload(UserTotemModel.totem))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_and_month_range(
        self,
        user_id: UUID,
        start_month: date,
        end_month: date,
        db: AsyncSession,
    ) -> list[UserTotemModel]:
        stmt = (
            select(UserTotemModel)
            .where(
                UserTotemModel.user_id == user_id,
                UserTotemModel.month >= start_month,
                UserTotemModel.month <= end_month,
            )
            .options(selectinload(UserTotemModel.totem))
            .order_by(UserTotemModel.month.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_user_month(
        self,
        user_id: UUID,
        month: date,
        db: AsyncSession,
    ) -> int:
        result = await db.execute(
            delete(UserTotemModel)
            .where(UserTotemModel.user_id == user_id, UserTotemModel.month == month)
        )
        return result.rowcount

    async def create(
        self,
        user_id: UUID,
        totem_id: UUID,
        month: date,
        score_snapshot: float | None,
        db: AsyncSession,
    ) -> UserTotemModel:
        now = datetime.now(timezone.utc)
        user_totem = UserTotemModel(
            id=uuid.uuid4(),
            created_at=now,
            updated_at=now,
            user_id=user_id,
            totem_id=totem_id,
            month=month,
            score_snapshot=score_snapshot,
        )
        db.add(user_totem)
        await db.flush()
        return user_totem
