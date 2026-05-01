from datetime import date, datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.evaluations.schemas import CRITERIA
from app.modules.feedbacks.model import UserMonthlyFeedbackModel


class WorstMessageEntry(BaseModel):
    text: str
    score: float


class WorstCategoryEntry(BaseModel):
    category: str
    mean_score: float
    worst_messages: list[WorstMessageEntry]


class LLMFeedbackInput(BaseModel):
    """Entrée structurée envoyée au LLM pour générer le feedback mensuel."""
    user_id: UUID
    period: str  # ex. "2026-03"
    worst_categories: list[WorstCategoryEntry]


class LLMFeedbackResult(BaseModel):
    """Sortie retournée par le LLM."""
    content: str
    worst_categories: list[str]

    def to_model(self, user_id: UUID, user_external_id: str, month: date) -> UserMonthlyFeedbackModel:
        return UserMonthlyFeedbackModel(
            user_id=user_id,
            user_external_id=user_external_id,
            month=month,
            content=self.content,
            worst_categories=self.worst_categories,
            generated_at=datetime.now(timezone.utc),
        )


class UserMonthlyFeedbackResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_external_id: str
    month: date
    content: str | None
    worst_categories: list[str] | None
    generated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def from_model(feedback: UserMonthlyFeedbackModel) -> "UserMonthlyFeedbackResponse":
        return UserMonthlyFeedbackResponse(
            id=feedback.id,
            user_id=feedback.user_id,
            user_external_id=feedback.user_external_id,
            month=feedback.month,
            content=feedback.content,
            worst_categories=feedback.worst_categories,
            generated_at=feedback.generated_at,
        )
