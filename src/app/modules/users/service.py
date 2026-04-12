from app.core.config.logs import LoggerManager
from app.modules.users.model import UserModel
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserResponse
from sqlalchemy.ext.asyncio import AsyncSession


class UserService:

    def __init__(
        self,
        logger: LoggerManager,
        db: AsyncSession,
        request_id: str,
        user_repository: UserRepository,
    ):
        self.tag = "SERVICE:User"
        self.logger = logger
        self.db = db
        self.request_id = request_id
        self.user_repository = user_repository

    async def get_by_external_id(self, external_id: str) -> UserResponse | None:
        user = await self.user_repository.get_by_external_id(
            external_id=external_id,
            db=self.db,
        )
        if not user:
            return None
        return UserResponse.model_validate(user)

    async def create(self, external_id: str) -> UserResponse:
        self.logger.info(
            tag=self.tag,
            message=f"Creating user external_id={external_id}",
            extra=self.request_id,
        )
        user = UserModel(external_id=external_id)
        await self.user_repository.create(user=user, db=self.db)
        return UserResponse.model_validate(user)
