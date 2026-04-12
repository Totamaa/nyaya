from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api.dependencies.db import get_db
from app.core.api.dependencies.request_id import get_request_id
from app.core.config.logs import get_logger
from app.modules.messages.repository import MessageRepository
from app.modules.messages.service import MessageService
from app.modules.users.dependencies import get_user_service
from app.modules.users.service import UserService


def get_message_repository() -> MessageRepository:
    return MessageRepository()


def get_message_service(
    logger=Depends(get_logger),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    user_service: UserService = Depends(get_user_service),
    message_repository: MessageRepository = Depends(get_message_repository),
) -> MessageService:
    return MessageService(
        logger=logger,
        db=db,
        request_id=request_id,
        user_service=user_service,
        message_repository=message_repository,
    )
