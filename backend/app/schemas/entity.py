from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    entity_type: str
    description: str | None
    jurisdiction: str | None
    risk_score: float | None
    risk_level: str | None
    identifiers: list[object]
    created_at: datetime


class EntityList(BaseModel):
    items: list[EntityRead]
    total: int


class EntityConnection(BaseModel):
    id: UUID
    relationship_type: str
    direction: str
    entity_id: UUID
    entity_name: str
    confidence: float | None
    verification_status: str


class EntityDetail(EntityRead):
    connections: list[EntityConnection]
