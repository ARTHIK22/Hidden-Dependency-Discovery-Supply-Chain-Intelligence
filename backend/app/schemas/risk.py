from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RiskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_id: UUID
    entity_name: str
    entity_type: str
    investigation_id: UUID | None
    score: float
    level: str
    reason: str
    created_at: datetime


class RiskList(BaseModel):
    items: list[RiskRead]
    total: int
