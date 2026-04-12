from fastapi import APIRouter, Depends, status

from app.modules.base.schemas import IdResponse
from app.modules.messages.dependencies import get_message_service
from app.modules.messages.schemas import CreateMessageRequest
from app.modules.messages.service import MessageService

router = APIRouter()


@router.post("/", response_model=IdResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    data: CreateMessageRequest,
    service: MessageService = Depends(get_message_service),
) -> IdResponse:
    return await service.create(request=data)
