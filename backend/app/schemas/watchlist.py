from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


WatchTargetType = Literal["entity", "relationship", "investigation", "risk_condition"]


class WatchlistCreate(BaseModel):
    target_type: WatchTargetType = "entity"
    target_id: UUID | None = None
    entity_id: UUID | None = None
    relationship_id: UUID | None = None
    investigation_id: UUID | None = None
    risk_threshold: float | None = Field(default=None, ge=0, le=100)
    condition_json: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def resolve_legacy_entity_input(self) -> "WatchlistCreate":
        if self.target_id is not None:
            return self
        if self.target_type == "entity" and self.entity_id is not None:
            self.target_id = self.entity_id
            return self
        if self.target_type == "relationship" and self.relationship_id is not None:
            self.target_id = self.relationship_id
            return self
        if self.target_type in {"investigation", "risk_condition"} and self.investigation_id is not None:
            self.target_id = self.investigation_id
            return self
        raise ValueError("A target ID matching target_type is required")


class WatchlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_type: WatchTargetType
    target_id: UUID | None
    entity_id: UUID | None
    relationship_id: UUID | None
    investigation_id: UUID | None
    status: str
    created_at: datetime
    entity_name: str
    entity_type: str
    risk_score: float | None
    risk_level: str | None
    risk_threshold: float | None
    condition_json: dict[str, object]
    is_demo: bool = False


class WatchlistList(BaseModel):
    items: list[WatchlistRead]
    total: int
