from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    id: UUID = Field(..., description="Internal UUID of the user.")
    external_id: str = Field(..., description="External identifier from the source backend.")

    model_config = ConfigDict(from_attributes=True)
