from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.logs import LoggerManager
from app.core.config.settings import get_settings
from app.modules.messages.repository import MessageRepository
from app.modules.users.exceptions import UserNotFoundException
from app.modules.users.model import UserModel
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserResponse


class UserService:

    def __init__(
        self,
        logger: LoggerManager,
        session: AsyncSession,
        request_id: str,
        user_repository: UserRepository,
        message_repository: MessageRepository,
    ):
        self.tag = "SERVICE:User"
        self.logger = logger
        self.session = session
        self.request_id = request_id
        self.user_repository = user_repository
        self.message_repository = message_repository

    async def get_by_external_id(self, external_id: str) -> UserResponse:
        user = await self.user_repository.get_by_external_id(
            external_id=external_id,
            db=self.session,
        )
        if not user:
            raise UserNotFoundException(external_id=external_id)
        return UserResponse.model_validate(user)

    async def get_eligible_user_ids_for_monthly_review(self) -> list[UUID]:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        period_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 1:
            period_start = period_end.replace(year=now.year - 1, month=12)
        else:
            period_start = period_end.replace(month=now.month - 1)

        return await self.message_repository.get_eligible_user_ids_for_monthly_review(
            db=self.session,
            period_start=period_start,
            period_end=period_end,
            min_messages=settings.REVIEW_MIN_MESSAGES,
        )

    async def create(self, external_id: str) -> UserResponse:
        self.logger.info(
            tag=self.tag,
            message=f"Creating user external_id={external_id}",
            extra=self.request_id,
        )
        user = UserModel(external_id=external_id)
        await self.user_repository.create(user=user, db=self.session)
        return UserResponse.model_validate(user)
