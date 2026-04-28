from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .constants import ALL_CRITERION_NAMES, TEXT_CRITERION_NAMES


ContextCompleteness = Literal["full", "partial", "low"]
ContentType = Literal["post", "comment"]
EvaluationStatus = Literal["success", "failed"]


class CriterionAssessment(BaseModel):
    score: float = Field(ge=1.0, le=5.0)
    rationale: str = Field(min_length=1, max_length=500)


class MessageRelation(BaseModel):
    content_id: str | None = None
    text: str | None = None
    author_id: str | int | None = None
    created_at: datetime | None = None


class MessageContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    edito_id: str | int | None = None
    topic_id: str | int | None = None
    phase: str | None = None
    tags: list[str] = Field(default_factory=list)
    topic_label: str | None = None
    edito_title: str | None = None


class MessageEvaluationInput(BaseModel):
    content_id: str = Field(min_length=1)
    content_type: ContentType
    text: str = Field(min_length=1)
    created_at: datetime
    author_id: str | int
    tenant_id: str = Field(default="default", min_length=1)
    likes_normalized: float = Field(default=0.0, ge=0.0, le=1.0)
    evaluation_requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    language: str | None = "fr"
    parent: MessageRelation | None = None
    thread_root: MessageRelation | None = None
    context: MessageContext | None = None

    @model_validator(mode="before")
    @classmethod
    def coerce_legacy_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        payload = dict(value)

        if "parent" not in payload:
            if any(
                key in payload
                for key in (
                    "parent_content_id",
                    "parent_text",
                    "parent_author_id",
                    "parent_created_at",
                )
            ):
                payload["parent"] = {
                    "content_id": payload.pop("parent_content_id", None),
                    "text": payload.pop("parent_text", None),
                    "author_id": payload.pop("parent_author_id", None),
                    "created_at": payload.pop("parent_created_at", None),
                }

        if "thread_root" not in payload:
            if any(key in payload for key in ("thread_root_id", "thread_root_text")):
                payload["thread_root"] = {
                    "content_id": payload.pop("thread_root_id", None),
                    "text": payload.pop("thread_root_text", None),
                }

        return payload

    @model_validator(mode="after")
    def validate_nested_payload(self) -> "MessageEvaluationInput":
        if self.content_type == "comment" and self.parent and not self.parent.text:
            raise ValueError("`parent.text` est requis quand `parent` est fourni.")
        if self.thread_root and not self.thread_root.text:
            raise ValueError("`thread_root.text` est requis quand `thread_root` est fourni.")
        return self

    def raw_context_snapshot(self) -> dict[str, Any]:
        return {
            "content_type": self.content_type,
            "text": self.text,
            "parent": None if self.parent is None else self.parent.model_dump(mode="json"),
            "thread_root": (
                None if self.thread_root is None else self.thread_root.model_dump(mode="json")
            ),
            "context": None if self.context is None else self.context.model_dump(mode="json"),
        }


class PreparedEvaluationInput(BaseModel):
    content_id: str
    content_type: ContentType
    text: str
    created_at: datetime
    author_id: str | int
    tenant_id: str
    likes_normalized: float = Field(ge=0.0, le=1.0)
    parent_text: str | None = None
    thread_root_text: str | None = None
    context_text: str | None = None
    context_completeness: ContextCompleteness

    def prompt_payload(self) -> dict[str, Any]:
        return {
            "message": {
                "content_type": self.content_type,
                "text": self.text,
            },
            "context": {
                "parent_text": self.parent_text,
                "thread_root_text": self.thread_root_text,
                "context_text": self.context_text,
            },
        }

    def snapshot(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SingleCriterionBenchmarkOutput(BaseModel):
    score: float = Field(ge=1.0, le=5.0)
    rationale: str = Field(min_length=1, max_length=500)


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
    model_confidence: float = Field(ge=0.0, le=1.0)

    def text_scores(self) -> dict[str, CriterionAssessment]:
        return {name: getattr(self, name) for name in TEXT_CRITERION_NAMES}


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
            raise ValueError(f"Scores manquants dans le résultat: {', '.join(missing)}")
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
    prepared_snapshot: dict[str, Any]
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
