import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.evaluations.model import EvaluationModel
from app.modules.evaluations.schemas import CRITERIA
from app.modules.messages.model import MessageModel


class EvaluationFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        message: MessageModel,
        **kwargs,
    ) -> EvaluationModel:
        scores = {
            field: kwargs.get(field, round(random.uniform(0.0, 10.0), 2))
            for field in CRITERIA
        }
        score_total = kwargs.get(
            "score_total", round(sum(scores.values()) / len(scores), 2)
        )
        evaluation = EvaluationModel(
            message_id=message.id,
            **scores,
            score_total=score_total,
            likes=kwargs.get("likes", 0),
        )
        session.add(evaluation)
        await session.flush()
        return evaluation
