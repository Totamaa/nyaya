from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api.dependencies.db import get_session
from app.core.api.dependencies.request_id import get_request_id
from app.core.config.logs import get_logger
from app.modules.evaluations.dependencies import get_evaluation_service
from app.modules.evaluations.service import EvaluationService
from app.modules.messages.repository import MessageRepository
from app.modules.messages.service import MessageService
from app.modules.users.dependencies import get_user_service
from app.modules.users.service import UserService


def get_message_repository() -> MessageRepository:
    return MessageRepository()


def get_message_service(
    logger=Depends(get_logger),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
    user_service: UserService = Depends(get_user_service),
    message_repository: MessageRepository = Depends(get_message_repository),
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
) -> MessageService:
    return MessageService(
        logger=logger,
        session=session,
        request_id=request_id,
        user_service=user_service,
        message_repository=message_repository,
        evaluation_service=evaluation_service,
    )
