from pydantic import BaseModel

from uuid import UUID
from app.modules.totems.model import TotemModel


class TotemAssignment(BaseModel):
    """Assignation pré-calculée transmise au worker via Taskiq."""
    totem_code: str
    score_snapshot: float


class TotemResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    category: str | None
    threshold: float | None

    model_config = {"from_attributes": True}

    @staticmethod
    def from_model(totem: TotemModel) -> "TotemResponse":
        return TotemResponse(
            id=totem.id,
            code=totem.code,
            name=totem.name,
            description=totem.description,
            category=totem.category,
            threshold=totem.threshold,
        )
