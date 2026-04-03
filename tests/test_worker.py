import asyncio
from pathlib import Path
from typing import Any

from llm.evaluation.models import LLMMessageEvaluationOutput, MessageEvaluationInput
from llm.evaluation.service import MessageEvaluationService
from llm.evaluation.storage import JsonlEvaluationEventSink, JsonlEvaluationRepository
from llm.evaluation.worker import AsyncMessageEvaluationWorker


class FakeLLMClient:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls = 0

    def complete_text(self, messages, *, temperature=None, max_tokens=None):
        raise NotImplementedError

    def stream_text(self, messages, *, temperature=None, max_tokens=None):
        raise NotImplementedError

    def complete_structured(self, messages, output_type, *, temperature=None, max_tokens=None):
        self.calls += 1
        return self.response if isinstance(self.response, output_type) else output_type.model_validate(self.response)


def build_output() -> LLMMessageEvaluationOutput:
    return LLMMessageEvaluationOutput.model_validate(
        {
            "clarte_des_idees": {"score": 4, "rationale": "Clair."},
            "exactitude_verifiabilite": {"score": 4, "rationale": "Prudent."},
            "pertinence": {"score": 4, "rationale": "Pertinent."},
            "logique_coherence": {"score": 4, "rationale": "Cohérent."},
            "absence_de_sophismes": {"score": 4, "rationale": "RAS."},
            "ouverture_d_esprit": {"score": 4, "rationale": "Nuancé."},
            "volonte_de_comprendre": {"score": 4, "rationale": "Ouvert."},
            "contribution_utile": {"score": 4, "rationale": "Utile."},
            "respect_collaboration": {"score": 4, "rationale": "Respectueux."},
            "analysis_summary": "Bon message.",
            "context_completeness": "partial",
            "model_confidence": 0.75,
        }
    )


def build_requests() -> list[MessageEvaluationInput]:
    return [
        MessageEvaluationInput.model_validate(
            {
                "content_id": f"c_{idx}",
                "content_type": "post",
                "text": f"Message {idx}",
                "created_at": "2026-03-01T09:00:00Z",
                "author_id": idx,
                "likes_normalized": 0.1 * idx,
                "tenant_id": "nyaya-test",
                "evaluation_requested_at": "2026-03-01T09:01:00Z",
            }
        )
        for idx in range(1, 4)
    ]


def test_worker_processes_batch(tmp_path: Path) -> None:
    repository = JsonlEvaluationRepository(tmp_path / "evaluations.jsonl")
    event_sink = JsonlEvaluationEventSink(tmp_path / "events.jsonl")
    service = MessageEvaluationService(
        client=FakeLLMClient(build_output()),
        repository=repository,
        event_sink=event_sink,
        model_name="fake-model",
    )
    worker = AsyncMessageEvaluationWorker(service, concurrency=2)

    records = asyncio.run(worker.process_batch(build_requests()))

    assert len(records) == 3
    assert {record.content_id for record in records} == {"c_1", "c_2", "c_3"}
    assert all(record.status == "success" for record in records)
