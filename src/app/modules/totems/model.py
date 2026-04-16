from sqlalchemy import Column, Float, String, Text
from sqlalchemy.orm import relationship

from app.modules.base.model import BaseModel


class TotemModel(BaseModel):
    __tablename__ = "totems"

    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    threshold = Column(Float, nullable=True)

    user_totems = relationship(
        "UserTotemModel",
        back_populates="totem",
        passive_deletes=True,
    )
