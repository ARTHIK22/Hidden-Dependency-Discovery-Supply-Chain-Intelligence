from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str
    confidence: float | None
    source: str | None
    evidence_summary: str | None
    verification_status: str
    verification: dict[str, object] | None = None
    evidence_count: int = 0
    sources: list[str] = Field(default_factory=list)
    conflict_flag: bool = False
