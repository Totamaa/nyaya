from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.modules.base.model import BaseModel


class UserMonthlyFeedbackModel(BaseModel):
    __tablename__ = "user_monthly_feedbacks"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    month = Column(Date, nullable=False)
    content = Column(Text, nullable=True)
    worst_categories = Column(JSONB, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship(
        "UserModel",
        back_populates="monthly_feedbacks",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "month", name="uq_user_monthly_feedbacks_user_month"),
        Index("ix_user_monthly_feedbacks_user_id", "user_id"),
    )
