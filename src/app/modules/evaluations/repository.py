from uuid import UUID

from sqlalchemy import func, select
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

    async def get_criterion_ranking(
        self,
        criterion: str,
        db: AsyncSession,
    ) -> list[tuple[UUID, float]]:
        """Retourne [(user_id, avg_score), ...] trié DESC pour un critère donné."""
        col = getattr(EvaluationModel, criterion)
        stmt = (
            select(MessageModel.author_id, func.avg(col).label("avg"))
            .join(EvaluationModel, EvaluationModel.message_id == MessageModel.id)
            .where(col.is_not(None))
            .group_by(MessageModel.author_id)
            .order_by(func.avg(col).desc())
        )
        rows = await db.execute(stmt)
        return [(row.author_id, float(row.avg)) for row in rows]

    async def get_global_ranking(
        self,
        db: AsyncSession,
    ) -> list[tuple[UUID, float]]:
        """Retourne [(user_id, avg_score_total), ...] trié DESC."""
        stmt = (
            select(MessageModel.author_id, func.avg(EvaluationModel.score_total).label("avg"))
            .join(EvaluationModel, EvaluationModel.message_id == MessageModel.id)
            .where(EvaluationModel.score_total.is_not(None))
            .group_by(MessageModel.author_id)
            .order_by(func.avg(EvaluationModel.score_total).desc())
        )
        rows = await db.execute(stmt)
        return [(row.author_id, float(row.avg)) for row in rows]
