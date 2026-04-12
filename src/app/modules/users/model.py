from sqlalchemy import Column, Date, String, Text, ForeignKey, Interval
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.modules.base.model import BaseModel

class UserModel(BaseModel):
    __tablename__ = "users"

    backend_id = Column(String(255), unique=True, nullable=False)
