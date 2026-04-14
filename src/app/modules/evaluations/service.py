import random
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.logs import LoggerManager
from app.modules.evaluations.model import EvaluationModel
from app.modules.evaluations.repository import EvaluationRepository
from app.modules.evaluations.schemas import EvaluationResponse


def _simulate_llm_evaluation(text: str) -> dict:
    """
    Stub: simulates the LLM evaluation call.
    To be replaced by the real LLM connector once available.
    """
    scores = [round(random.uniform(0, 10), 2) for _ in range(9)]
    keys = [
        "clarte_des_idees",
        "exactitude_verifiabilite",
        "pertinence",
        "logique_coherence",
        "absence_de_sophismes",
        "ouverture_d_esprit",
        "volonte_de_comprendre",
        "contribution_utile",
        "respect_collaboration",
    ]
    result = dict(zip(keys, scores))
    result["score_total"] = round(sum(scores) / len(scores), 2)
    return result


class EvaluationService:

    def __init__(
        self,
        logger: LoggerManager,
        db: AsyncSession,
        request_id: str,
        evaluation_repository: EvaluationRepository,
    ):
        self.tag = "SERVICE:Evaluation"
        self.logger = logger
        self.db = db
        self.request_id = request_id
        self.evaluation_repository = evaluation_repository

    async def evaluate(self, message_text: str, message_id: UUID) -> EvaluationResponse:
        self.logger.info(
            tag=self.tag,
            message=f"Evaluating message_id={message_id}",
            extra=self.request_id,
        )

        scores = _simulate_llm_evaluation(message_text)

        evaluation = EvaluationModel(
            message_id=message_id,
            **scores,
        )
        await self.evaluation_repository.create(evaluation=evaluation, db=self.db)

        self.logger.info(
            tag=self.tag,
            message=f"Evaluation created id={evaluation.id} score_total={evaluation.score_total}",
            extra=self.request_id,
        )

        return EvaluationResponse.from_model(evaluation)

    async def get_by_message_id(self, message_id: UUID) -> EvaluationResponse | None:
        evaluation = await self.evaluation_repository.get_by_message_id(
            message_id=message_id,
            db=self.db,
        )
        if not evaluation:
            return None
        return EvaluationResponse.from_model(evaluation)
