import asyncio
import random
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.logs import LoggerManager
from app.core.config.settings import get_settings
from app.modules.evaluations.exceptions import EvaluationNotFoundException, LLMTimeoutException
from app.modules.evaluations.repository import EvaluationRepository
from app.modules.evaluations.schemas import EvaluationResponse, LLMEvaluationResult
from app.modules.messages.schemas import CreateMessageRequest


async def _simulate_llm_evaluation(request: CreateMessageRequest) -> LLMEvaluationResult:
    """
    Stub: simulates the LLM evaluation call.
    To be replaced by the real LLM connector once available.
    The real implementation will use `request` (text, context, parent, etc.).
    """
    _ = request  # unused in stub, will be consumed by the real LLM connector
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
    return LLMEvaluationResult(**result)


class EvaluationService:

    def __init__(
        self,
        logger: LoggerManager,
        session: AsyncSession,
        request_id: str,
        evaluation_repository: EvaluationRepository,
    ):
        self.tag = "SERVICE:Evaluation"
        self.logger = logger
        self.session = session
        self.request_id = request_id
        self.evaluation_repository = evaluation_repository

    async def evaluate(self, request: CreateMessageRequest, message_id: UUID) -> EvaluationResponse:
        self.logger.info(
            tag=self.tag,
            message=f"Evaluating message_id={message_id}",
            extra=self.request_id,
        )

        settings = get_settings()
        timeout = settings.LLM_TIMEOUT_SECONDS
        try:
            llm_result = await asyncio.wait_for(
                _simulate_llm_evaluation(request),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise LLMTimeoutException(timeout_seconds=timeout)

        evaluation = llm_result.to_model(message_id=message_id)
        await self.evaluation_repository.create(evaluation=evaluation, db=self.session)

        self.logger.info(
            tag=self.tag,
            message=f"Evaluation created id={evaluation.id} score_total={evaluation.score_total}",
            extra=self.request_id,
        )

        return EvaluationResponse.from_model(evaluation)

    async def get_by_message_external_id(self, message_external_id: str) -> EvaluationResponse:
        evaluation = await self.evaluation_repository.get_by_message_external_id(
            external_id=message_external_id,
            db=self.session,
        )
        if not evaluation:
            raise EvaluationNotFoundException(message_external_id=message_external_id)
        return EvaluationResponse.from_model(evaluation)
