from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.modules.totems.schemas import TotemResponse
from app.modules.user_totems.model import UserTotemModel


class UserTotemResponse(BaseModel):
    id: UUID
    user_id: UUID
    totem_id: UUID
    month: date
    score_snapshot: float | None
    totem: TotemResponse

    model_config = {"from_attributes": True}

    @staticmethod
    def from_model(user_totem: UserTotemModel) -> "UserTotemResponse":
        return UserTotemResponse(
            id=user_totem.id,
            user_id=user_totem.user_id,
            totem_id=user_totem.totem_id,
            month=user_totem.month,
            score_snapshot=user_totem.score_snapshot,
            totem=TotemResponse.from_model(user_totem.totem),
        )
