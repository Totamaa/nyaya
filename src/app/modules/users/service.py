from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.logs import LoggerManager
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
    ):
        self.tag = "SERVICE:User"
        self.logger = logger
        self.session = session
        self.request_id = request_id
        self.user_repository = user_repository

    async def get_by_external_id(self, external_id: str) -> UserResponse:
        user = await self.user_repository.get_by_external_id(
            external_id=external_id,
            db=self.session,
        )
        if not user:
            raise UserNotFoundException(external_id=external_id)
        return UserResponse.model_validate(user)

    async def create(self, external_id: str) -> UserResponse:
        self.logger.info(
            tag=self.tag,
            message=f"Creating user external_id={external_id}",
            extra=self.request_id,
        )
        user = UserModel(external_id=external_id)
        await self.user_repository.create(user=user, db=self.session)
        return UserResponse.model_validate(user)
