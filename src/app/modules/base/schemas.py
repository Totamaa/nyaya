from pydantic import BaseModel, Field
from uuid import UUID

class IdResponse(BaseModel):
    id: UUID = Field(..., description="ID of the resource")
