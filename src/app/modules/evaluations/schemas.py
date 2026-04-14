from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.evaluations.model import EvaluationModel


class LLMEvaluationResult(BaseModel):
    """Scores returned by the LLM connector."""
    clarte_des_idees: float | None
    exactitude_verifiabilite: float | None
    pertinence: float | None
    logique_coherence: float | None
    absence_de_sophismes: float | None

    ouverture_d_esprit: float | None
    volonte_de_comprendre: float | None
    contribution_utile: float | None
    respect_collaboration: float | None

    score_total: float | None

    def to_model(self, message_id: UUID) -> EvaluationModel:
        return EvaluationModel(
            message_id=message_id,
            clarte_des_idees=self.clarte_des_idees,
            exactitude_verifiabilite=self.exactitude_verifiabilite,
            pertinence=self.pertinence,
            logique_coherence=self.logique_coherence,
            absence_de_sophismes=self.absence_de_sophismes,
            ouverture_d_esprit=self.ouverture_d_esprit,
            volonte_de_comprendre=self.volonte_de_comprendre,
            contribution_utile=self.contribution_utile,
            respect_collaboration=self.respect_collaboration,
            score_total=self.score_total,
        )


class EvaluationResponse(BaseModel):
    id: UUID
    message_id: UUID

    clarte_des_idees: float | None
    exactitude_verifiabilite: float | None
    pertinence: float | None
    logique_coherence: float | None
    absence_de_sophismes: float | None

    ouverture_d_esprit: float | None
    volonte_de_comprendre: float | None
    contribution_utile: float | None
    respect_collaboration: float | None

    likes: int
    score_total: float | None

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def from_model(evaluation: EvaluationModel) -> "EvaluationResponse":
        return EvaluationResponse(
            id=evaluation.id,
            message_id=evaluation.message_id,
            clarte_des_idees=evaluation.clarte_des_idees,
            exactitude_verifiabilite=evaluation.exactitude_verifiabilite,
            pertinence=evaluation.pertinence,
            logique_coherence=evaluation.logique_coherence,
            absence_de_sophismes=evaluation.absence_de_sophismes,
            ouverture_d_esprit=evaluation.ouverture_d_esprit,
            volonte_de_comprendre=evaluation.volonte_de_comprendre,
            contribution_utile=evaluation.contribution_utile,
            respect_collaboration=evaluation.respect_collaboration,
            likes=evaluation.likes,
            score_total=evaluation.score_total,
        )
