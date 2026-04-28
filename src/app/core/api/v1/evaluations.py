from fastapi import APIRouter, Depends, status

from app.modules.evaluations.dependencies import get_evaluation_service
from app.modules.evaluations.schemas import EvaluationResponse
from app.modules.evaluations.service import EvaluationService

router = APIRouter()


@router.get("/{message_external_id}", response_model=EvaluationResponse, status_code=status.HTTP_200_OK)
async def get_evaluation(
    message_external_id: str,
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationResponse:
    return await service.get_by_message_external_id(message_external_id=message_external_id)
