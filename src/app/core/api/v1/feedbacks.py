from fastapi import APIRouter, Depends, status

from app.modules.feedbacks.dependencies import get_feedback_service
from app.modules.feedbacks.schemas import UserMonthlyFeedbackResponse
from app.modules.feedbacks.service import FeedbackService

router = APIRouter()


@router.get("/{user_external_id}/{year_month}/feedback", response_model=UserMonthlyFeedbackResponse, status_code=status.HTTP_200_OK)
async def get_feedback(
    user_external_id: str,
    year_month: str,
    service: FeedbackService = Depends(get_feedback_service),
) -> UserMonthlyFeedbackResponse:
    return await service.get_by_user_and_month(user_external_id=user_external_id, year_month=year_month)
