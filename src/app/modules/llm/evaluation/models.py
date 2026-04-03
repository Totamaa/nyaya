from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from .constants import ALL_CRITERION_NAMES, TEXT_CRITERION_NAMES


ContextCompleteness = Literal["full", "partial", "low"]
ContentType = Literal["post", "comment"]
EvaluationStatus = Literal["success", "failed"]


class CriterionAssessment(BaseModel):
    score: float = Field(ge=1.0, le=5.0)
    rationale: str = Field(min_length=1, max_length=500)


class MessageEvaluationInput(BaseModel):
    content_id: str = Field(min_length=1)
    content_type: ContentType
    text: str = Field(min_length=1)
    created_at: datetime
    author_id: str | int
    parent_content_id: str | None = None
    parent_text: str | None = None
    parent_author_id: str | int | None = None
    parent_created_at: datetime | None = None
    thread_root_id: str | None = None
    thread_root_text: str | None = None
    likes_normalized: float = Field(ge=0.0, le=1.0)
    tenant_id: str = Field(min_length=1)
    evaluation_requested_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )

    @model_validator(mode="after")
    def validate_thread_root(self) -> "MessageEvaluationInput":
        if self.thread_root_id and not self.thread_root_text:
            raise ValueError("`thread_root_text` est requis quand `thread_root_id` est fourni.")
        return self

    def context_snapshot(self) -> dict[str, Any]:
        return {
            "content_type": self.content_type,
            "text": self.text,
            "parent": (
                None
                if not any(
                    value is not None
                    for value in (
                        self.parent_content_id,
                        self.parent_text,
                        self.parent_author_id,
                        self.parent_created_at,
                    )
                )
                else {
                    "content_id": self.parent_content_id,
                    "text": self.parent_text,
                    "author_id": self.parent_author_id,
                    "created_at": self.parent_created_at.isoformat()
                    if self.parent_created_at
                    else None,
                }
            ),
            "thread_root": (
                None
                if self.thread_root_id is None and self.thread_root_text is None
                else {
                    "content_id": self.thread_root_id,
                    "text": self.thread_root_text,
                }
            ),
        }


class LLMMessageEvaluationOutput(BaseModel):
    clarte_des_idees: CriterionAssessment
    exactitude_verifiabilite: CriterionAssessment
    pertinence: CriterionAssessment
    logique_coherence: CriterionAssessment
    absence_de_sophismes: CriterionAssessment
    ouverture_d_esprit: CriterionAssessment
    volonte_de_comprendre: CriterionAssessment
    contribution_utile: CriterionAssessment
    respect_collaboration: CriterionAssessment
    analysis_summary: str = Field(min_length=1, max_length=1000)
    context_completeness: ContextCompleteness
    model_confidence: float = Field(ge=0.0, le=1.0)

    def text_scores(self) -> dict[str, CriterionAssessment]:
        return {
            name: getattr(self, name)
            for name in TEXT_CRITERION_NAMES
        }


class MessageEvaluationResult(BaseModel):
    content_id: str
    author_id: str | int
    tenant_id: str
    scores: dict[str, CriterionAssessment]
    weighted_score: float = Field(ge=0.0, le=1.0)
    score_100: float = Field(ge=0.0, le=100.0)
    analysis_summary: str
    context_completeness: ContextCompleteness
    model_confidence: float = Field(ge=0.0, le=1.0)
    evaluation_version: str
    evaluated_at: datetime

    @model_validator(mode="after")
    def validate_all_scores_present(self) -> "MessageEvaluationResult":
        missing = [name for name in ALL_CRITERION_NAMES if name not in self.scores]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Scores manquants dans le résultat: {joined}")
        return self


class PersistedEvaluationRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: str(uuid4()))
    content_id: str
    author_id: str | int
    tenant_id: str
    evaluation_version: str
    prompt_version: str
    model_name: str
    status: EvaluationStatus
    input_snapshot: MessageEvaluationInput
    context_snapshot: dict[str, Any]
    result: MessageEvaluationResult | None = None
    likes_normalized: float = Field(ge=0.0, le=1.0)
    likes_score: float | None = Field(default=None, ge=1.0, le=5.0)
    failure_reason: str | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluationEvent(BaseModel):
    event_type: Literal["message_evaluated", "message_evaluation_failed"]
    content_id: str
    tenant_id: str
    evaluation_version: str
    record_id: str
    status: EvaluationStatus
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
