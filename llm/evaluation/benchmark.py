from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from llm.connectors.base import LLMClient

from .datasets import (
    EndToEndControlDataset,
    EndToEndControlItem,
    FallacyControlDataset,
    FallacyControlItem,
    RangeControlDataset,
    RangeControlItem,
    load_dataset,
)
from .models import MessageEvaluationInput, MessageEvaluationResult
from .service import MessageEvaluationService
from .storage import JsonlEvaluationEventSink, JsonlEvaluationRepository


CRITERION_ALIASES: dict[str, str] = {
    "clarity": "clarte_des_idees",
    "clarte_des_idees": "clarte_des_idees",
    "fact_vs_opinion": "exactitude_verifiabilite",
    "exactitude_verifiabilite": "exactitude_verifiabilite",
    "relevance": "pertinence",
    "pertinence": "pertinence",
    "logic_coherence": "logique_coherence",
    "logique_coherence": "logique_coherence",
    "respect_collaboration": "respect_collaboration",
    "ouverture_d_esprit": "ouverture_d_esprit",
    "open_mindedness": "ouverture_d_esprit",
    "volonte_de_comprendre": "volonte_de_comprendre",
    "understanding": "volonte_de_comprendre",
    "contribution_utile": "contribution_utile",
    "useful_contribution": "contribution_utile",
}


class FallacyBenchmarkOutput(BaseModel):
    fallacy_present: str = Field(pattern="^(yes|no)$")
    fallacy_type: str = Field(min_length=1)
    rationale: str = Field(min_length=1, max_length=500)


class BenchmarkItemResult(BaseModel):
    dataset_name: str
    item_id: str
    status: str
    expected: dict[str, Any]
    actual: dict[str, Any] | None = None
    error: str | None = None


class BenchmarkDatasetSummary(BaseModel):
    dataset_name: str
    total: int
    passed: int
    failed: int
    accuracy: float
    results: list[BenchmarkItemResult]


class BenchmarkReport(BaseModel):
    backend_model: str
    dataset_count: int
    total_items: int
    passed_items: int
    failed_items: int
    overall_accuracy: float
    summaries: list[BenchmarkDatasetSummary]


@dataclass(slots=True)
class BenchmarkRunner:
    client: LLMClient
    model_name: str
    system_prompt: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = 1600

    def _make_service(self) -> MessageEvaluationService:
        temp_dir = Path(tempfile.mkdtemp(prefix="nyaya-benchmark-"))
        return MessageEvaluationService(
            client=self.client,
            repository=JsonlEvaluationRepository(temp_dir / "evaluations.jsonl"),
            event_sink=JsonlEvaluationEventSink(temp_dir / "events.jsonl"),
            model_name=self.model_name,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    def _range_item_to_input(
        self,
        dataset: RangeControlDataset,
        item: RangeControlItem,
    ) -> MessageEvaluationInput:
        return MessageEvaluationInput.model_validate(
            {
                "content_id": f"{dataset.dataset_name}:{item.id}",
                "content_type": "comment",
                "text": item.message,
                "created_at": "2026-01-01T00:00:00Z",
                "author_id": "benchmark",
                "parent_content_id": f"parent:{item.id}",
                "parent_text": item.previous_message,
                "parent_author_id": "context",
                "parent_created_at": "2026-01-01T00:00:00Z",
                "likes_normalized": 0.5,
                "tenant_id": "benchmark",
                "evaluation_requested_at": "2026-01-01T00:00:00Z",
            }
        )

    def _benchmark_range_dataset(self, dataset: RangeControlDataset) -> BenchmarkDatasetSummary:
        service = self._make_service()
        criterion_key = dataset.criterion or dataset.dataset_name.removesuffix("_control")
        mapped_criterion = CRITERION_ALIASES.get(criterion_key)
        if mapped_criterion is None:
            raise ValueError(f"Critère non mappé pour le dataset {dataset.dataset_name!r}.")

        results: list[BenchmarkItemResult] = []
        for item in dataset.items:
            try:
                evaluation = service.evaluate(self._range_item_to_input(dataset, item))
                predicted = evaluation.scores[mapped_criterion].score
                low, high = item.expected_score_range
                passed = low <= predicted <= high
                results.append(
                    BenchmarkItemResult(
                        dataset_name=dataset.dataset_name,
                        item_id=item.id,
                        status="passed" if passed else "failed",
                        expected={"score_range": [low, high], "criterion": mapped_criterion},
                        actual={
                            "predicted_score": predicted,
                            "rationale": evaluation.scores[mapped_criterion].rationale,
                        },
                    )
                )
            except Exception as exc:
                results.append(
                    BenchmarkItemResult(
                        dataset_name=dataset.dataset_name,
                        item_id=item.id,
                        status="failed",
                        expected={
                            "score_range": list(item.expected_score_range),
                            "criterion": mapped_criterion,
                        },
                        error=str(exc),
                    )
                )
        return _build_summary(dataset.dataset_name, results)

    def _build_fallacy_messages(self, item: FallacyControlItem) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "Tu détectes les sophismes dans un message. "
                    "Réponds uniquement avec un JSON strict : "
                    '{"fallacy_present":"yes|no","fallacy_type":"ad_hominem|false_dilemma|hasty_generalization|none","rationale":"court texte"}'
                ),
            },
            {
                "role": "user",
                "content": (
                    "Contexte:\n"
                    f"{item.context}\n\n"
                    "Message:\n"
                    f"{item.message}\n\n"
                    "Détermine s'il y a un sophisme parmi: ad_hominem, false_dilemma, hasty_generalization."
                ),
            },
        ]

    def _benchmark_fallacy_dataset(self, dataset: FallacyControlDataset) -> BenchmarkDatasetSummary:
        results: list[BenchmarkItemResult] = []
        for item in dataset.items:
            try:
                output = self.client.complete_structured(
                    self._build_fallacy_messages(item),
                    FallacyBenchmarkOutput,
                    temperature=self.temperature,
                    max_tokens=min(self.max_tokens or 600, 600),
                )
                passed = (
                    output.fallacy_present == item.expected.fallacy_present
                    and output.fallacy_type == item.expected.fallacy_type
                )
                results.append(
                    BenchmarkItemResult(
                        dataset_name=dataset.dataset_name,
                        item_id=item.id,
                        status="passed" if passed else "failed",
                        expected=item.expected.model_dump(),
                        actual=output.model_dump(),
                    )
                )
            except Exception as exc:
                results.append(
                    BenchmarkItemResult(
                        dataset_name=dataset.dataset_name,
                        item_id=item.id,
                        status="failed",
                        expected=item.expected.model_dump(),
                        error=str(exc),
                    )
                )
        return _build_summary(dataset.dataset_name, results)

    def _benchmark_end_to_end_item(
        self,
        service: MessageEvaluationService,
        item: EndToEndControlItem,
    ) -> BenchmarkItemResult:
        request = MessageEvaluationInput.model_validate(item.input)
        evaluation = service.evaluate(request)
        low, high = item.expected.expected_score_range
        passed = (
            low <= evaluation.score_100 <= high
            and evaluation.context_completeness == item.expected.context_completeness
        )
        return BenchmarkItemResult(
            dataset_name="message_eval_end_to_end",
            item_id=item.id,
            status="passed" if passed else "failed",
            expected=item.expected.model_dump(),
            actual={
                "score_100": evaluation.score_100,
                "context_completeness": evaluation.context_completeness,
                "analysis_summary": evaluation.analysis_summary,
            },
        )

    def _benchmark_end_to_end_dataset(
        self,
        dataset: EndToEndControlDataset,
    ) -> BenchmarkDatasetSummary:
        service = self._make_service()
        results: list[BenchmarkItemResult] = []
        for item in dataset.items:
            try:
                results.append(self._benchmark_end_to_end_item(service, item))
            except Exception as exc:
                results.append(
                    BenchmarkItemResult(
                        dataset_name=dataset.dataset_name,
                        item_id=item.id,
                        status="failed",
                        expected=item.expected.model_dump(),
                        error=str(exc),
                    )
                )
        return _build_summary(dataset.dataset_name, results)

    def run_paths(self, dataset_paths: list[str | Path]) -> BenchmarkReport:
        summaries: list[BenchmarkDatasetSummary] = []
        for dataset_path in dataset_paths:
            dataset = load_dataset(dataset_path)
            if isinstance(dataset, RangeControlDataset):
                summaries.append(self._benchmark_range_dataset(dataset))
            elif isinstance(dataset, FallacyControlDataset):
                summaries.append(self._benchmark_fallacy_dataset(dataset))
            else:
                summaries.append(self._benchmark_end_to_end_dataset(dataset))

        total_items = sum(summary.total for summary in summaries)
        passed_items = sum(summary.passed for summary in summaries)
        failed_items = sum(summary.failed for summary in summaries)
        accuracy = 0.0 if total_items == 0 else round(passed_items / total_items, 4)
        return BenchmarkReport(
            backend_model=self.model_name,
            dataset_count=len(summaries),
            total_items=total_items,
            passed_items=passed_items,
            failed_items=failed_items,
            overall_accuracy=accuracy,
            summaries=summaries,
        )


def _build_summary(dataset_name: str, results: list[BenchmarkItemResult]) -> BenchmarkDatasetSummary:
    total = len(results)
    passed = sum(1 for result in results if result.status == "passed")
    failed = total - passed
    accuracy = 0.0 if total == 0 else round(passed / total, 4)
    return BenchmarkDatasetSummary(
        dataset_name=dataset_name,
        total=total,
        passed=passed,
        failed=failed,
        accuracy=accuracy,
        results=results,
    )
