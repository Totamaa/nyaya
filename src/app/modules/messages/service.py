from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import UnitOfWork
from app.core.config.logs import LoggerManager
from app.modules.base.schemas import IdResponse
from app.modules.evaluations.service import EvaluationService
from app.modules.messages.repository import MessageRepository
from app.modules.messages.schemas import CreateMessageRequest
from app.modules.users.service import UserService


class MessageService:

    def __init__(
        self,
        logger: LoggerManager,
        db: AsyncSession,
        request_id: str,
        user_service: UserService,
        message_repository: MessageRepository,
        evaluation_service: EvaluationService,
    ):
        self.tag = "SERVICE:Message"
        self.logger = logger
        self.db = db
        self.request_id = request_id
        self.user_service = user_service
        self.message_repository = message_repository
        self.evaluation_service = evaluation_service

    async def create(self, request: CreateMessageRequest) -> IdResponse:
        self.logger.info(
            tag=self.tag,
            message=f"Ingesting message external_id={request.content_id}",
            extra=self.request_id,
        )

        async with UnitOfWork(self.db):
            user = await self.user_service.get_by_external_id(str(request.author_id))
            if not user:
                user = await self.user_service.create(str(request.author_id))

            parent_id = None
            if request.parent:
                parent = await self.message_repository.get_by_external_id(
                    external_id=request.parent.content_id,
                    db=self.db,
                )
                if parent:
                    parent_id = parent.id

            root_id = None
            if request.thread_root:
                root = await self.message_repository.get_by_external_id(
                    external_id=request.thread_root.content_id,
                    db=self.db,
                )
                if root:
                    root_id = root.id

            message = request.to_model(author=user, parent_id=parent_id, root_id=root_id)
            await self.message_repository.create(message=message, db=self.db)
            await self.evaluation_service.evaluate(
                message_text=request.text,
                message_id=message.id,
            )

        self.logger.info(
            tag=self.tag,
            message=f"Message created id={message.id} external_id={message.external_id}",
            extra=self.request_id,
        )

        return IdResponse(id=message.id)
