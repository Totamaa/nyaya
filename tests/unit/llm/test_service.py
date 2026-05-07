from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from llm.evaluation.models import LLMMessageEvaluationOutput, MessageEvaluationInput
from llm.evaluation.service import MessageEvaluationService
from llm.evaluation.storage import JsonlEvaluationEventSink, JsonlEvaluationRepository


def build_input() -> MessageEvaluationInput:
    return MessageEvaluationInput.model_validate(
        {
            "content_id": "c_100",
            "content_type": "comment",
            "text": "Je comprends le besoin, mais il faudrait comparer le gain attendu et le risque avant de supprimer cette validation.",
            "created_at": "2026-03-01T10:00:00Z",
            "author_id": 7,
            "parent": {
                "content_id": "c_099",
                "text": "Il faut supprimer cette validation.",
                "author_id": 4,
                "created_at": "2026-03-01T09:58:00Z",
            },
            "context": {"phase": "decision", "topic_label": "workflow achat"},
            "likes_normalized": 0.25,
            "tenant_id": "nyaya-test",
            "evaluation_requested_at": "2026-03-01T10:01:00Z",
        }
    )


def build_output() -> LLMMessageEvaluationOutput:
    return LLMMessageEvaluationOutput.model_validate(
        {
            "clarte_des_idees": {"score": 4, "rationale": "Clair."},
            "exactitude_verifiabilite": {"score": 4, "rationale": "Nuancé."},
            "pertinence": {"score": 5, "rationale": "Très pertinent."},
            "logique_coherence": {"score": 4, "rationale": "Raisonnement cohérent."},
            "absence_de_sophismes": {"score": 5, "rationale": "Pas de sophisme manifeste."},
            "ouverture_d_esprit": {"score": 5, "rationale": "Nuance explicite."},
            "volonte_de_comprendre": {"score": 3, "rationale": "Cherche partiellement à comprendre."},
            "contribution_utile": {"score": 4, "rationale": "Propose un cadre utile."},
            "respect_collaboration": {"score": 5, "rationale": "Ton respectueux."},
            "analysis_summary": "Message globalement solide et constructif.",
            "model_confidence": 0.88,
        }
    )


class FakeLLMClient:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict[str, str]]] = []

    def complete_text(self, messages, *, temperature=None, max_tokens=None):
        raise NotImplementedError

    def stream_text(self, messages, *, temperature=None, max_tokens=None):
        raise NotImplementedError

    def complete_structured(self, messages, output_type, *, temperature=None, max_tokens=None):
        self.calls.append(messages)
        if not self.responses:
            raise RuntimeError("No fake response left.")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, output_type):
            return response
        return output_type.model_validate(response)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_service(tmp_path: Path, client: FakeLLMClient) -> MessageEvaluationService:
    repository = JsonlEvaluationRepository(tmp_path / "evaluations.jsonl")
    event_sink = JsonlEvaluationEventSink(tmp_path / "events.jsonl")
    return MessageEvaluationService(
        client=client,
        repository=repository,
        event_sink=event_sink,
        model_name="fake-model",
    )


@pytest.mark.unit
def test_service_retries_once_and_persists_success(tmp_path: Path) -> None:
    client = FakeLLMClient([ValueError("bad-json"), build_output()])
    service = build_service(tmp_path, client)

    record = service.process(build_input())

    assert record.status == "success"
    assert record.result is not None
    assert len(client.calls) == 2
    assert record.result.scores["likes"].score == 2.0
    assert record.result.context_completeness == "full"
    assert record.result.score_100 > 0

    evaluations = read_jsonl(tmp_path / "evaluations.jsonl")
    events = read_jsonl(tmp_path / "events.jsonl")
    assert len(evaluations) == 1
    assert len(events) == 1
    assert events[0]["event_type"] == "message_evaluated"


@pytest.mark.unit
def test_service_is_idempotent_for_same_content_and_version(tmp_path: Path) -> None:
    client = FakeLLMClient([build_output()])
    service = build_service(tmp_path, client)
    request = build_input()

    first = service.process(request)
    second = service.process(request)

    assert first.record_id == second.record_id
    assert len(client.calls) == 1
    assert len(read_jsonl(tmp_path / "evaluations.jsonl")) == 1
    assert len(read_jsonl(tmp_path / "events.jsonl")) == 1


@pytest.mark.unit
def test_service_persists_failure_after_retry_exhausted(tmp_path: Path) -> None:
    client = FakeLLMClient([ValueError("bad-json"), ValueError("still-bad")])
    service = build_service(tmp_path, client)

    record = service.process(build_input())

    assert record.status == "failed"
    assert record.result is None
    assert "still-bad" in (record.failure_reason or "")
    assert len(client.calls) == 2

    evaluations = read_jsonl(tmp_path / "evaluations.jsonl")
    events = read_jsonl(tmp_path / "events.jsonl")
    assert evaluations[0]["status"] == "failed"
    assert events[0]["event_type"] == "message_evaluation_failed"
