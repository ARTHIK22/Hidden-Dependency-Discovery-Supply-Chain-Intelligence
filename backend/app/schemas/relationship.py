from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RelationshipCreate(BaseModel):
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str = Field(min_length=1, max_length=100)
    description: str | None = None
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    metadata_json: dict = Field(default_factory=dict)


class RelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str
    description: str | None
    confidence_score: float
    verification_status: str
    strength: float
    metadata_json: dict
    discovered_at: datetime
    updated_at: datetime


class RelationshipVerificationRead(BaseModel):
    relationship: RelationshipRead
    verification: dict
