from fastapi import APIRouter, Depends, status

from app.modules.totems.dependencies import get_totem_service
from app.modules.totems.schemas import TotemResponse
from app.modules.totems.service import TotemService

router = APIRouter()


@router.get("/", response_model=list[TotemResponse], status_code=status.HTTP_200_OK)
async def get_all_totems(
    service: TotemService = Depends(get_totem_service),
) -> list[TotemResponse]:
    return await service.get_all()
