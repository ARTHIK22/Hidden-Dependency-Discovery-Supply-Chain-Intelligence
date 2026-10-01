from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    relationship_id: UUID | None
    relationship_type: str | None
    source_entity_id: UUID | None
    source_entity_name: str | None
    target_entity_id: UUID | None
    target_entity_name: str | None
    source: str
    source_type: str
    published_date: date | None
    captured_at: datetime
    confidence: float | None
    verification_status: str
    excerpt: str
    source_url: str | None
    title: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    relationship_verification: dict[str, object] | None = None


class EvidenceList(BaseModel):
    items: list[EvidenceRead]
    total: int
