from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class EvidenceCreate(BaseModel):
    investigation_id: UUID | None = None
    source_id: UUID | None = None
    entity_id: UUID | None = None
    relationship_id: UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1, max_length=100)
    confidence_score: float = Field(default=0, ge=0, le=1)
    url: HttpUrl | None = None
    published_at: datetime | None = None
    metadata_json: dict = Field(default_factory=dict)


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    investigation_id: UUID | None
    source_id: UUID | None
    entity_id: UUID | None
    relationship_id: UUID | None
    title: str
    content: str
    evidence_type: str
    confidence_score: float
    url: str | None
    content_hash: str | None
    verification_status: str
    collected_at: datetime
    published_at: datetime | None
    metadata_json: dict
