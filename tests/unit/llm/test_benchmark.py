from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from llm.evaluation.benchmark import BenchmarkRunner
from llm.evaluation.models import LLMMessageEvaluationOutput, SingleCriterionBenchmarkOutput


class FakeLLMClient:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)

    def complete_text(self, messages, *, temperature=None, max_tokens=None):
        raise NotImplementedError

    def stream_text(self, messages, *, temperature=None, max_tokens=None):
        raise NotImplementedError

    def complete_structured(self, messages, output_type, *, temperature=None, max_tokens=None):
        if not self.responses:
            raise RuntimeError("No fake response left.")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, output_type):
            return response
        return output_type.model_validate(response)


def build_full_eval(score: int = 5) -> LLMMessageEvaluationOutput:
    return LLMMessageEvaluationOutput.model_validate(
        {
            "clarte_des_idees": {"score": score, "rationale": "ok"},
            "exactitude_verifiabilite": {"score": score, "rationale": "ok"},
            "pertinence": {"score": score, "rationale": "ok"},
            "logique_coherence": {"score": score, "rationale": "ok"},
            "absence_de_sophismes": {"score": score, "rationale": "ok"},
            "ouverture_d_esprit": {"score": score, "rationale": "ok"},
            "volonte_de_comprendre": {"score": score, "rationale": "ok"},
            "contribution_utile": {"score": score, "rationale": "ok"},
            "respect_collaboration": {"score": score, "rationale": "ok"},
            "analysis_summary": "ok",
            "model_confidence": 0.9,
        }
    )


def build_single(score: int = 5) -> SingleCriterionBenchmarkOutput:
    return SingleCriterionBenchmarkOutput.model_validate({"score": score, "rationale": "ok"})


@pytest.mark.unit
def test_benchmark_runner_on_selected_datasets() -> None:
    client = FakeLLMClient(
        [
            build_single(5),
            build_single(1),
            {"fallacy_present": "yes", "fallacy_type": "ad_hominem", "rationale": "ok"},
        ]
    )
    runner = BenchmarkRunner(client=client, model_name="fake-model", max_tokens=500)
    report = runner.run_paths(
        [
            Path("tests/data/llm/relevance_control.json"),
            Path("tests/data/llm/fallacies_control.json"),
        ]
    )

    assert report.dataset_count == 2
    assert report.total_items == 40
    assert report.failed_items >= 1


@pytest.mark.unit
def test_benchmark_runner_respects_explicit_range_dataset_failure() -> None:
    client = FakeLLMClient([build_single(1)])
    runner = BenchmarkRunner(client=client, model_name="fake-model", max_tokens=500)
    report = runner.run_paths([Path("tests/data/llm/clarity_control.json")])

    assert report.dataset_count == 1
    assert report.summaries[0].dataset_name == "clarity_control"
    assert report.summaries[0].total == 20
