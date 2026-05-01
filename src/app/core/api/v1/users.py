from fastapi import APIRouter, Depends, Query, status

from app.modules.feedbacks.dependencies import get_feedback_service
from app.modules.feedbacks.schemas import UserMonthlyFeedbackResponse
from app.modules.feedbacks.service import FeedbackService
from app.modules.totems.dependencies import get_totem_service
from app.modules.totems.service import TotemService
from app.modules.user_totems.schemas import UserTotemResponse

router = APIRouter()


@router.get(
    "/{user_external_id}/{year_month}/totems",
    response_model=list[UserTotemResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user_totems_by_month(
    user_external_id: str,
    year_month: str,
    service: TotemService = Depends(get_totem_service),
) -> list[UserTotemResponse]:
    return await service.get_by_user_and_month(
        user_external_id=user_external_id,
        year_month=year_month,
    )


@router.get(
    "/{user_external_id}/totems",
    response_model=list[UserTotemResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user_totems_history(
    user_external_id: str,
    limit: int = Query(6, ge=1, le=24),
    offset: int = Query(0, ge=0),
    service: TotemService = Depends(get_totem_service),
) -> list[UserTotemResponse]:
    return await service.get_history_by_user(
        user_external_id=user_external_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{user_external_id}/feedbacks",
    response_model=list[UserMonthlyFeedbackResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user_feedbacks_history(
    user_external_id: str,
    limit: int = Query(6, ge=1, le=24),
    offset: int = Query(0, ge=0),
    service: FeedbackService = Depends(get_feedback_service),
) -> list[UserMonthlyFeedbackResponse]:
    return await service.get_history_by_user(
        user_external_id=user_external_id,
        limit=limit,
        offset=offset,
    )
