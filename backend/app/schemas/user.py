from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
