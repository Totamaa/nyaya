from __future__ import annotations

import threading
from datetime import UTC, datetime

from app.core.config.logs import get_logger
from app.modules.llm.connectors.base import LLMClient

logger = get_logger()
_TAG = "LLM:EvalService"

from .constants import EVALUATION_VERSION, PROMPT_VERSION
from .models import (
    EvaluationEvent,
    LLMMessageEvaluationOutput,
    MessageEvaluationInput,
    MessageEvaluationResult,
    PreparedEvaluationInput,
    PersistedEvaluationRecord,
)
from .preparation import prepare_message_for_evaluation
from .prompt import build_evaluation_messages
from .scoring import build_scores, compute_likes_score, compute_weighted_score
from .storage import JsonlEvaluationEventSink, JsonlEvaluationRepository


class MessageEvaluationService:
    def __init__(
        self,
        *,
        client: LLMClient,
        repository: JsonlEvaluationRepository,
        event_sink: JsonlEvaluationEventSink,
        model_name: str,
        prompt_version: str = PROMPT_VERSION,
        evaluation_version: str = EVALUATION_VERSION,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = 1600,
    ) -> None:
        self.client = client
        self.repository = repository
        self.event_sink = event_sink
        self.model_name = model_name
        self.prompt_version = prompt_version
        self.evaluation_version = evaluation_version
        self.system_prompt = system_prompt
        self.temperature = float(temperature)
        self.max_tokens = max_tokens
        self._locks_guard = threading.Lock()
        self._locks: dict[tuple[str, str], threading.Lock] = {}

    def _get_lock(self, content_id: str) -> threading.Lock:
        key = (content_id, self.evaluation_version)
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

    def _call_llm(
        self,
        prepared_input: PreparedEvaluationInput,
        *,
        max_retries: int = 2,
    ) -> LLMMessageEvaluationOutput:
        last_error: Exception | None = None
        messages = build_evaluation_messages(
            prepared_input,
            system_prompt=self.system_prompt,
        )
        for attempt in range(max_retries):
            try:
                logger.debug(_TAG, f"LLM call attempt {attempt + 1}/{max_retries}")
                return self.client.complete_structured(
                    messages,
                    LLMMessageEvaluationOutput,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception as exc:
                last_error = exc
                logger.warning(_TAG, f"LLM attempt {attempt + 1} failed", extra=str(exc)[:120])
                if attempt < max_retries - 1:
                    messages = messages + [
                        {
                            "role": "user",
                            "content": (
                                "La réponse précédente n'était pas un JSON strict valide ou complet. "
                                "Réponds uniquement avec le JSON demandé, sans markdown ni texte additionnel."
                            ),
                        }
                    ]
        raise last_error or RuntimeError("Échec LLM inconnu")

    def _build_success_record(
        self,
        message_input: MessageEvaluationInput,
        prepared_input: PreparedEvaluationInput,
        llm_output: LLMMessageEvaluationOutput,
    ) -> PersistedEvaluationRecord:
        evaluated_at = datetime.now(UTC)
        likes_score = compute_likes_score(prepared_input.likes_normalized)
        scores = build_scores(
            llm_output,
            likes_normalized=prepared_input.likes_normalized,
        )
        weighted_score, score_100 = compute_weighted_score(scores)
        result = MessageEvaluationResult(
            content_id=message_input.content_id,
            author_id=message_input.author_id,
            tenant_id=message_input.tenant_id,
            scores=scores,
            weighted_score=weighted_score,
            score_100=score_100,
            analysis_summary=llm_output.analysis_summary,
            context_completeness=prepared_input.context_completeness,
            model_confidence=llm_output.model_confidence,
            evaluation_version=self.evaluation_version,
            evaluated_at=evaluated_at,
        )
        return PersistedEvaluationRecord(
            content_id=message_input.content_id,
            author_id=message_input.author_id,
            tenant_id=message_input.tenant_id,
            evaluation_version=self.evaluation_version,
            prompt_version=self.prompt_version,
            model_name=self.model_name,
            status="success",
            input_snapshot=message_input,
            prepared_snapshot=prepared_input.snapshot(),
            result=result,
            likes_normalized=prepared_input.likes_normalized,
            likes_score=likes_score,
            evaluated_at=evaluated_at,
        )

    def _build_failure_record(
        self,
        message_input: MessageEvaluationInput,
        prepared_input: PreparedEvaluationInput,
        failure_reason: str,
    ) -> PersistedEvaluationRecord:
        return PersistedEvaluationRecord(
            content_id=message_input.content_id,
            author_id=message_input.author_id,
            tenant_id=message_input.tenant_id,
            evaluation_version=self.evaluation_version,
            prompt_version=self.prompt_version,
            model_name=self.model_name,
            status="failed",
            input_snapshot=message_input,
            prepared_snapshot=prepared_input.snapshot(),
            likes_normalized=prepared_input.likes_normalized,
            likes_score=compute_likes_score(prepared_input.likes_normalized),
            failure_reason=failure_reason,
        )

    def process(
        self, message_input: MessageEvaluationInput
    ) -> PersistedEvaluationRecord:
        lock = self._get_lock(message_input.content_id)
        with lock:
            existing = self.repository.get(
                message_input.content_id,
                self.evaluation_version,
            )
            if existing is not None:
                logger.debug(_TAG, "Cache hit, skipping evaluation", extra=f"content_id={message_input.content_id}")
                return existing

            logger.info(_TAG, "Evaluating message", extra=f"content_id={message_input.content_id} model={self.model_name}")
            prepared_input = prepare_message_for_evaluation(message_input)
            try:
                llm_output = self._call_llm(prepared_input)
                record = self._build_success_record(
                    message_input, prepared_input, llm_output
                )
                logger.info(_TAG, "Evaluation success", extra=f"content_id={message_input.content_id}")
            except Exception as exc:
                logger.error(_TAG, "Evaluation failed", extra=f"content_id={message_input.content_id} reason={exc}", exc=exc)
                record = self._build_failure_record(
                    message_input, prepared_input, str(exc)
                )

            persisted = self.repository.append(record)
            if persisted.record_id == record.record_id:
                event_type = (
                    "message_evaluated"
                    if persisted.status == "success"
                    else "message_evaluation_failed"
                )
                self.event_sink.emit(
                    EvaluationEvent(
                        event_type=event_type,
                        content_id=persisted.content_id,
                        tenant_id=persisted.tenant_id,
                        evaluation_version=persisted.evaluation_version,
                        record_id=persisted.record_id,
                        status=persisted.status,
                    )
                )
            return persisted

    def evaluate(
        self, message_input: MessageEvaluationInput
    ) -> MessageEvaluationResult:
        record = self.process(message_input)
        if record.result is None:
            raise RuntimeError(record.failure_reason or "Échec d'évaluation inconnu.")
        return record.result
