from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api.dependencies.db import get_session
from app.core.api.dependencies.request_id import get_request_id
from app.core.config.logs import get_logger
from app.modules.totems.repository import TotemRepository
from app.modules.totems.service import TotemService
from app.modules.user_totems.dependencies import get_user_totem_repository
from app.modules.user_totems.repository import UserTotemRepository
from app.modules.users.dependencies import get_user_repository
from app.modules.users.repository import UserRepository


def get_totem_repository() -> TotemRepository:
    return TotemRepository()


def get_totem_service(
    logger=Depends(get_logger),
    session: AsyncSession = Depends(get_session),
    request_id: str = Depends(get_request_id),
    totem_repository: TotemRepository = Depends(get_totem_repository),
    user_totem_repository: UserTotemRepository = Depends(get_user_totem_repository),
    user_repository: UserRepository = Depends(get_user_repository),
) -> TotemService:
    return TotemService(
        logger=logger,
        session=session,
        request_id=request_id,
        totem_repository=totem_repository,
        user_totem_repository=user_totem_repository,
        user_repository=user_repository,
    )
