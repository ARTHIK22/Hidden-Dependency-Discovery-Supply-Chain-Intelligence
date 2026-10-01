from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID | None
    entity_id: UUID | None
    relationship_id: UUID | None = None
    entity_name: str | None
    title: str
    message: str
    alert_type: str = "risk"
    severity: str
    reason: str | None = None
    risk_score: float | None = None
    evidence_ids: list[str] = []
    risk_snapshot: dict[str, object] | None = None
    demo_only: bool = False
    read_at: datetime | None
    dismissed_at: datetime | None
    created_at: datetime


class AlertList(BaseModel):
    items: list[AlertRead]
    total: int
