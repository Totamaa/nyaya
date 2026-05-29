from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.logs import LoggerManager
from app.core.config.settings import get_settings
from app.modules.evaluations.exceptions import EvaluationNotFoundException
from app.modules.evaluations.repository import EvaluationRepository
from app.modules.evaluations.schemas import EvaluationResponse, LLMEvaluationResult
from app.modules.llm.connectors.factory import build_llm_client
from app.modules.llm.evaluation import evaluate_message
from app.modules.llm.evaluation.models import MessageEvaluationInput
from app.modules.messages.schemas import CreateMessageRequest


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
        eval_input = MessageEvaluationInput(
            content_id=request.content_id,
            content_type=request.content_type,
            text=request.text,
            created_at=request.created_at,
            author_id=request.author_id,
            context=request.context.model_dump() if request.context else None,
            parent=request.parent.model_dump() if request.parent else None,
            thread_root=request.thread_root.model_dump() if request.thread_root else None,
        )
        client = build_llm_client(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            timeout_s=float(settings.LLM_TIMEOUT_SECONDS),
            use_mock=settings.LLM_USE_MOCK,
        )
        raw = evaluate_message(client, eval_input)
        llm_result = LLMEvaluationResult(**raw)

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

    async def get_all_rankings(
        self,
        criteria: list[str],
    ) -> tuple[list[tuple[str, list[tuple[UUID, float]]]], list[tuple[UUID, float]]]:
        """Calcule les rankings par critère + global. Appelé une fois par l'orchestrateur."""
        criteria_rankings = [
            (crit, await self.evaluation_repository.get_criterion_ranking(crit, self.session))
            for crit in criteria
        ]
        global_ranking = await self.evaluation_repository.get_global_ranking(self.session)
        return criteria_rankings, global_ranking
