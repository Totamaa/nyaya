from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.evaluations.model import EvaluationModel
from app.modules.messages.model import MessageModel


class EvaluationRepository:

    async def get_by_message_id(
        self,
        message_id: UUID,
        db: AsyncSession,
    ) -> EvaluationModel | None:
        stmt = select(EvaluationModel).where(EvaluationModel.message_id == message_id)
        result = await db.execute(stmt)
        return result.scalars().one_or_none()

    async def get_by_message_external_id(
        self,
        external_id: str,
        db: AsyncSession,
    ) -> EvaluationModel | None:
        stmt = (
            select(EvaluationModel)
            .join(MessageModel, MessageModel.id == EvaluationModel.message_id)
            .where(MessageModel.external_id == external_id)
        )
        result = await db.execute(stmt)
        return result.scalars().one_or_none()

    async def create(
        self,
        evaluation: EvaluationModel,
        db: AsyncSession,
    ) -> EvaluationModel:
        db.add(evaluation)
        await db.flush()
        return evaluation
