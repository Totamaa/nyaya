from sqlalchemy import Column, Date, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.modules.base.model import BaseModel


class UserTotemModel(BaseModel):
    __tablename__ = "user_totems"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    totem_id = Column(UUID(as_uuid=True), ForeignKey("totems.id", ondelete="CASCADE"), nullable=False)
    month = Column(Date, nullable=False)
    score_snapshot = Column(Float, nullable=True)

    user = relationship(
        "UserModel",
        back_populates="totems",
        passive_deletes=True,
    )
    totem = relationship(
        "TotemModel",
        back_populates="user_totems",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "totem_id", "month", name="uq_user_totems_user_totem_month"),
        Index("ix_user_totems_user_id", "user_id"),
        Index("ix_user_totems_month", "month"),
    )
