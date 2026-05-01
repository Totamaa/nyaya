from fastapi import APIRouter, Depends, status

from app.modules.totems.dependencies import get_totem_service
from app.modules.totems.service import TotemService
from app.modules.user_totems.schemas import UserTotemResponse

router = APIRouter()


@router.get(
    "/{user_external_id}/{year_month}/totems",
    response_model=list[UserTotemResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user_totems(
    user_external_id: str,
    year_month: str,
    service: TotemService = Depends(get_totem_service),
) -> list[UserTotemResponse]:
    return await service.get_by_user_and_month(
        user_external_id=user_external_id,
        year_month=year_month,
    )
