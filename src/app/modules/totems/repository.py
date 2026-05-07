from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.totems.model import TotemModel


class TotemRepository:

    async def get_all(self, db: AsyncSession) -> list[TotemModel]:
        result = await db.execute(select(TotemModel))
        return list(result.scalars().all())

    async def get_by_codes(self, codes: list[str], db: AsyncSession) -> list[TotemModel]:
        result = await db.execute(
            select(TotemModel).where(TotemModel.code.in_(codes))
        )
        return list(result.scalars().all())
