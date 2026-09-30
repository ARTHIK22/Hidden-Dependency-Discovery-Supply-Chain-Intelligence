from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID | None
    entity_id: UUID | None
    entity_name: str | None
    title: str
    message: str
    severity: str
    read_at: datetime | None
    dismissed_at: datetime | None
    created_at: datetime


class AlertList(BaseModel):
    items: list[AlertRead]
    total: int
