from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.messages.model import MessageModel


class MessageRepository:

    async def get_by_external_id(
        self,
        external_id: str,
        db: AsyncSession,
    ) -> MessageModel | None:
        stmt = select(MessageModel).where(MessageModel.external_id == external_id)
        result = await db.execute(stmt)
        return result.scalars().one_or_none()

    async def create(
        self,
        message: MessageModel,
        db: AsyncSession,
    ) -> MessageModel:
        db.add(message)
        return message
