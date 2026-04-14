from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.evaluations.model import EvaluationModel


class EvaluationRepository:

    async def get_by_message_id(
        self,
        message_id: UUID,
        db: AsyncSession,
    ) -> EvaluationModel | None:
        stmt = select(EvaluationModel).where(EvaluationModel.message_id == message_id)
        result = await db.execute(stmt)
        return result.scalars().one_or_none()

    async def create(
        self,
        evaluation: EvaluationModel,
        db: AsyncSession,
    ) -> EvaluationModel:
        db.add(evaluation)
        return evaluation
