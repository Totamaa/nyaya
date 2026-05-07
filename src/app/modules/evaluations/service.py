import asyncio
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.logs import LoggerManager
from app.core.config.settings import get_settings
from app.modules.evaluations.exceptions import (
    EvaluationNotFoundException,
    LLMAuthenticationException,
    LLMContextLengthException,
    LLMInvalidResponseException,
    LLMQuotaExceededException,
    LLMRateLimitException,
    LLMTimeoutException,
    LLMUnavailableException,
)
from app.modules.evaluations.repository import EvaluationRepository
from app.modules.evaluations.schemas import EvaluationResponse, LLMEvaluationResult
from app.modules.llm.config import load_config
from app.modules.llm.connectors.factory import build_llm
from app.modules.llm.evaluation.models import MessageEvaluationInput
from app.modules.llm.evaluation.service import MessageEvaluationService
from app.modules.llm.evaluation.storage import JsonlEvaluationEventSink, JsonlEvaluationRepository
from app.modules.messages.repository import MessageRepository
from app.modules.messages.schemas import CreateMessageRequest

_LLM_EVALUATION_SERVICE: MessageEvaluationService | None = None


def _get_llm_evaluation_service() -> MessageEvaluationService:
    global _LLM_EVALUATION_SERVICE
    if _LLM_EVALUATION_SERVICE is not None:
        return _LLM_EVALUATION_SERVICE

    root_dir = Path(__file__).resolve().parents[4]
    llm_cfg = load_config(root_dir / "src/app/modules/llm/config.toml")
    llm_client = build_llm(llm_cfg)
    _LLM_EVALUATION_SERVICE = MessageEvaluationService(
        client=llm_client,
        repository=JsonlEvaluationRepository(root_dir / "data/message_evaluations.jsonl"),
        event_sink=JsonlEvaluationEventSink(root_dir / "data/message_evaluation_events.jsonl"),
        model_name=(
            llm_cfg.ollama.model
            if llm_cfg.llm.backend == "ollama"
            else llm_cfg.mistral.model
        ),
        system_prompt=llm_cfg.llm.system_prompt,
        temperature=llm_cfg.llm.temperature,
        max_tokens=llm_cfg.llm.max_tokens,
    )
    return _LLM_EVALUATION_SERVICE


async def _to_llm_input(
    request: CreateMessageRequest,
    *,
    session: AsyncSession,
) -> MessageEvaluationInput:
    message_repository = MessageRepository()
    parent_payload = None
    if request.parent:
        parent = await message_repository.get_by_external_id(
            external_id=request.parent.content_id,
            db=session,
        )
        if parent and parent.text:
            parent_payload = {
                "content_id": request.parent.content_id,
                "text": parent.text,
            }

    thread_root_payload = None
    if request.thread_root:
        thread_root = await message_repository.get_by_external_id(
            external_id=request.thread_root.content_id,
            db=session,
        )
        if thread_root and thread_root.text:
            thread_root_payload = {
                "content_id": request.thread_root.content_id,
                "text": thread_root.text,
            }

    return MessageEvaluationInput(
        content_id=request.content_id,
        content_type=request.content_type,
        text=request.text,
        created_at=request.created_at,
        author_id=str(request.author_id),
        parent=parent_payload,
        thread_root=thread_root_payload,
        context=(
            request.context.model_dump(mode="json", exclude_none=True)
            if request.context
            else None
        ),
        likes_normalized=0.0,
    )


async def _call_real_llm(
    request: CreateMessageRequest,
    *,
    session: AsyncSession,
) -> LLMEvaluationResult:
    llm_service = _get_llm_evaluation_service()
    llm_input = await _to_llm_input(request, session=session)
    llm_result = await asyncio.to_thread(llm_service.evaluate, llm_input)
    return LLMEvaluationResult(
        clarte_des_idees=llm_result.scores["clarte_des_idees"].score,
        exactitude_verifiabilite=llm_result.scores["exactitude_verifiabilite"].score,
        pertinence=llm_result.scores["pertinence"].score,
        logique_coherence=llm_result.scores["logique_coherence"].score,
        absence_de_sophismes=llm_result.scores["absence_de_sophismes"].score,
        ouverture_d_esprit=llm_result.scores["ouverture_d_esprit"].score,
        volonte_de_comprendre=llm_result.scores["volonte_de_comprendre"].score,
        contribution_utile=llm_result.scores["contribution_utile"].score,
        respect_collaboration=llm_result.scores["respect_collaboration"].score,
        score_total=round(llm_result.weighted_score * 5.0, 2),
    )


def _map_llm_error(exc: Exception) -> Exception:
    message = str(exc).lower()
    if "timed out" in message or "timeout" in message:
        timeout = get_settings().LLM_TIMEOUT_SECONDS
        return LLMTimeoutException(timeout_seconds=timeout)
    if "api key" in message or "authentication" in message or "unauthorized" in message:
        return LLMAuthenticationException()
    if "quota" in message or "credits" in message:
        return LLMQuotaExceededException()
    if "429" in message or "rate limit" in message:
        return LLMRateLimitException()
    if "502" in message or "503" in message or "unavailable" in message:
        return LLMUnavailableException()
    if "context length" in message or "too long" in message:
        return LLMContextLengthException()
    if "json" in message or "parse" in message or "pydantic" in message:
        return LLMInvalidResponseException(detail=str(exc))
    return LLMInvalidResponseException(detail=str(exc))


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
                _call_real_llm(request, session=self.session),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise LLMTimeoutException(timeout_seconds=timeout)
        except Exception as exc:
            raise _map_llm_error(exc) from exc

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
