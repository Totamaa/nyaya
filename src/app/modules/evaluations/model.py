from sqlalchemy import Column, Float, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.modules.base.model import BaseModel


class EvaluationModel(BaseModel):
    __tablename__ = "evaluations"

    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)

    clarte_des_idees = Column(Float, nullable=True)
    exactitude_verifiabilite = Column(Float, nullable=True)
    pertinence = Column(Float, nullable=True)
    logique_coherence = Column(Float, nullable=True)
    absence_de_sophismes = Column(Float, nullable=True)

    ouverture_d_esprit = Column(Float, nullable=True)
    volonte_de_comprendre = Column(Float, nullable=True)
    contribution_utile = Column(Float, nullable=True)
    respect_collaboration = Column(Float, nullable=True)

    likes = Column(Integer, default=0, nullable=False)
    score_total = Column(Float, nullable=True)

    message = relationship(
        "MessageModel",
        back_populates="evaluation",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("message_id", name="uq_evaluations_message_id"),
        Index("ix_evaluations_message_id", "message_id"),
    )
