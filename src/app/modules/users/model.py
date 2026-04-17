from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.modules.base.model import BaseModel


class UserModel(BaseModel):
    __tablename__ = "users"

    external_id = Column(String, unique=True, nullable=False, index=True)

    messages = relationship("MessageModel", back_populates="author", foreign_keys="MessageModel.author_id")
    totems = relationship("UserTotemModel", back_populates="user")
    monthly_feedbacks = relationship("UserMonthlyFeedbackModel", back_populates="user", foreign_keys="UserMonthlyFeedbackModel.user_id")
