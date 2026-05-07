from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.core.config.logs import LoggerManager
from app.modules.base.schemas import IdResponse
from app.modules.evaluations.service import EvaluationService
from app.modules.messages.exceptions import MessageAlreadyExistsException
from app.modules.messages.repository import MessageRepository
from app.modules.messages.schemas import CreateMessageRequest
from app.modules.users.exceptions import UserNotFoundException
from app.modules.users.service import UserService


class MessageService:

    def __init__(
        self,
        logger: LoggerManager,
        session: AsyncSession,
        request_id: str,
        user_service: UserService,
        message_repository: MessageRepository,
        evaluation_service: EvaluationService,
    ):
        self.tag = "SERVICE:Message"
        self.logger = logger
        self.session = session
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

        existing = await self.message_repository.get_by_external_id(
            external_id=str(request.content_id), db=self.session
        )
        if existing:
            raise MessageAlreadyExistsException()

        try:
            user = await self.user_service.get_by_external_id(str(request.author_id))
        except UserNotFoundException:
            user = await self.user_service.create(str(request.author_id))

        parent_id = None
        if request.parent:
            parent = await self.message_repository.get_by_external_id(
                external_id=request.parent.content_id,
                db=self.session,
            )
            if parent:
                parent_id = parent.id

        root_id = None
        if request.thread_root:
            root = await self.message_repository.get_by_external_id(
                external_id=request.thread_root.content_id,
                db=self.session,
            )
            if root:
                root_id = root.id

        message = request.to_model(author=user, parent_id=parent_id, root_id=root_id)
        await self.message_repository.create(message=message, db=self.session)
        try:
            await self.evaluation_service.evaluate(request=request, message_id=message.id)
        except ValidationError as exc:
            self.logger.warning(
                tag=self.tag,
                message=(
                    f"Evaluation skipped for message id={message.id}: "
                    f"invalid evaluation payload ({exc})"
                ),
                extra=self.request_id,
            )
        except Exception as exc:
            self.logger.warning(
                tag=self.tag,
                message=f"Evaluation failed for message id={message.id}: {exc}",
                extra=self.request_id,
            )

        self.logger.info(
            tag=self.tag,
            message=f"Message created id={message.id} external_id={message.external_id}",
            extra=self.request_id,
        )

        return IdResponse(id=message.id)
