from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api.dependencies.db import get_session
from app.core.api.dependencies.request_id import get_request_id
from app.core.config.logs import get_logger
from app.modules.feedbacks.repository import FeedbackRepository
from app.modules.feedbacks.service import FeedbackService
from app.modules.messages.repository import MessageRepository
from app.modules.users.repository import UserRepository


def get_feedback_repository() -> FeedbackRepository:
    return FeedbackRepository()


def get_feedback_service(
    logger=Depends(get_logger),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
    feedback_repository: FeedbackRepository = Depends(get_feedback_repository),
) -> FeedbackService:
    return FeedbackService(
        logger=logger,
        session=session,
        request_id=request_id,
        feedback_repository=feedback_repository,
        message_repository=MessageRepository(),
        user_repository=UserRepository(),
    )
