from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api.dependencies.db import get_db
from app.core.api.dependencies.request_id import get_request_id
from app.core.config.logs import get_logger
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService


def get_user_repository() -> UserRepository:
    return UserRepository()


def get_user_service(
    logger=Depends(get_logger),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(
        logger=logger,
        db=db,
        request_id=request_id,
        user_repository=user_repository,
    )
