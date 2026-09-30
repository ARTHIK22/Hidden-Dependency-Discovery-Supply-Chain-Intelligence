from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WatchlistCreate(BaseModel):
    entity_id: UUID


class WatchlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_id: UUID
    status: str
    created_at: datetime
    entity_name: str
    entity_type: str
    risk_score: float | None
    risk_level: str | None


class WatchlistList(BaseModel):
    items: list[WatchlistRead]
    total: int
