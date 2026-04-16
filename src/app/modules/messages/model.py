from sqlalchemy import Column, DateTime, Index, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.modules.base.model import BaseModel


class MessageModel(BaseModel):
    __tablename__ = "messages"

    external_id = Column(String, unique=True, nullable=False)
    content_type = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    source_created_at = Column(DateTime(timezone=True), nullable=True)

    edito_id = Column(Integer, nullable=True)
    topic_id = Column(Integer, nullable=True)
    phase = Column(String, nullable=True)
    tags = Column(JSONB, nullable=True)

    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    root_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)

    author = relationship(
        "UserModel",
        back_populates="messages",
        foreign_keys=[author_id],
        passive_deletes=True,
    )
    parent = relationship(
        "MessageModel",
        foreign_keys=[parent_id],
        remote_side="MessageModel.id",
        passive_deletes=True,
    )
    root = relationship(
        "MessageModel",
        foreign_keys=[root_id],
        remote_side="MessageModel.id",
        passive_deletes=True,
    )
    evaluation = relationship(
        "EvaluationModel",
        back_populates="message",
        uselist=False,
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_messages_author_id", "author_id"),
        Index("ix_messages_created_at", "created_at"),
    )
