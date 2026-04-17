from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.evaluations.model import EvaluationModel
from app.modules.messages.model import MessageModel


class MessageRepository:

    async def get_eligible_user_ids_for_monthly_review(
        self,
        db: AsyncSession,
        period_start: datetime,
        period_end: datetime,
        min_messages: int,
    ) -> list[UUID]:
        stmt = (
            select(MessageModel.author_id)
            .where(
                MessageModel.source_created_at >= period_start,
                MessageModel.source_created_at < period_end,
            )
            .group_by(MessageModel.author_id)
            .having(func.count(MessageModel.id) >= min_messages)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_external_id(
        self,
        external_id: str,
        db: AsyncSession,
    ) -> MessageModel | None:
        stmt = select(MessageModel).where(MessageModel.external_id == external_id)
        result = await db.execute(stmt)
        return result.scalars().one_or_none()

    async def get_messages_with_evaluations(
        self,
        user_id: UUID,
        period_start: datetime,
        period_end: datetime,
        db: AsyncSession,
    ) -> list[tuple[MessageModel, EvaluationModel]]:
        stmt = (
            select(MessageModel, EvaluationModel)
            .join(EvaluationModel, EvaluationModel.message_id == MessageModel.id)
            .where(
                MessageModel.author_id == user_id,
                MessageModel.source_created_at >= period_start,
                MessageModel.source_created_at < period_end,
            )
        )
        result = await db.execute(stmt)
        return list(result.all())

    async def create(
        self,
        message: MessageModel,
        db: AsyncSession,
    ) -> MessageModel:
        db.add(message)
        await db.flush()
        return message
