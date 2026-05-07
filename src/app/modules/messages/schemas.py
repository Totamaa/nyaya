from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.messages.model import MessageModel
from app.modules.users.schemas import UserResponse


class ParentRef(BaseModel):
    content_id: str
    text: str
    author_id: int | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class ThreadRootRef(BaseModel):
    content_id: str
    text: str

    model_config = ConfigDict(extra="forbid")


class MessageContext(BaseModel):
    edito_id: int | None = None
    topic_id: int | None = None
    phase: str | None = None
    tags: list[str] | None = None

    model_config = ConfigDict(extra="forbid")


class CreateMessageRequest(BaseModel):
    content_id: str = Field(..., description="External identifier from the source backend.")
    content_type: str = Field(..., description="Type of content (e.g. comment, reply).")
    text: str = Field(..., min_length=1, description="Text content of the message.")
    created_at: datetime = Field(..., description="Original creation date from the source backend.")
    author_id: int = Field(..., description="External user ID from the source backend.")
    likes: int | None = Field(None, ge=0, description="Number of likes the message has received.")
    parent: ParentRef | None = Field(None, description="Direct parent message reference, including its text.")
    thread_root: ThreadRootRef | None = Field(None, description="Root of the thread, including its text.")
    context: MessageContext | None = Field(None, description="Editorial context metadata.")

    model_config = ConfigDict(extra="forbid")

    def to_model(
        self,
        author: UserResponse,
        parent_id: UUID | None = None,
        root_id: UUID | None = None,
    ) -> MessageModel:
        context = self.context
        return MessageModel(
            external_id=self.content_id,
            content_type=self.content_type,
            text=self.text,
            source_created_at=self.created_at,
            author_id=author.id,
            likes=self.likes,
            parent_id=parent_id,
            root_id=root_id,
            edito_id=context.edito_id if context else None,
            topic_id=context.topic_id if context else None,
            phase=context.phase if context else None,
            tags=context.tags if context else None,
        )


class MessageResponse(BaseModel):
    id: UUID
    external_id: str
    content_type: str
    text: str
    source_created_at: datetime | None
    created_at: datetime
    author_id: UUID
    likes: int | None
    parent_id: UUID | None
    root_id: UUID | None
    edito_id: int | None
    topic_id: int | None
    phase: str | None
    tags: list[str] | None

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def from_model(message: MessageModel) -> "MessageResponse":
        return MessageResponse(
            id=message.id,
            external_id=message.external_id,
            content_type=message.content_type,
            text=message.text,
            source_created_at=message.source_created_at,
            created_at=message.created_at,
            author_id=message.author_id,
            likes=message.likes,
            parent_id=message.parent_id,
            root_id=message.root_id,
            edito_id=message.edito_id,
            topic_id=message.topic_id,
            phase=message.phase,
            tags=message.tags,
        )
