from datetime import datetime, timezone

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.messages.model import MessageModel
from app.modules.users.model import UserModel

fake = Faker()


class MessageFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        author: UserModel,
        **kwargs,
    ) -> MessageModel:
        message = MessageModel(
            external_id=kwargs.get("external_id", str(fake.uuid4())),
            content_type=kwargs.get("content_type", "text"),
            text=kwargs.get("text", fake.paragraph()),
            author_id=author.id,
            source_created_at=kwargs.get(
                "source_created_at", datetime.now(timezone.utc)
            ),
            parent_id=kwargs.get("parent_id"),
            root_id=kwargs.get("root_id"),
            edito_id=kwargs.get("edito_id"),
            topic_id=kwargs.get("topic_id"),
            phase=kwargs.get("phase"),
            tags=kwargs.get("tags"),
        )
        session.add(message)
        await session.flush()
        return message

    @staticmethod
    def build(author_id, **kwargs) -> MessageModel:
        return MessageModel(
            external_id=kwargs.get("external_id", str(fake.uuid4())),
            content_type=kwargs.get("content_type", "text"),
            text=kwargs.get("text", fake.paragraph()),
            author_id=author_id,
        )
