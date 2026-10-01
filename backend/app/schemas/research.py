from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResearchEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    at: datetime
    type: str
    message: str
    step_id: str | None = None
    query: str | None = None


class ResearchProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str
    current_step: str | None = None
    completed_steps: int = 0
    total_steps: int = 0
    current_query: str | None = None
    sources_found: int = 0
    evidence_found: int = 0
    entities_found: int = 0
    relationships_found: int = 0
    elapsed_seconds: float = 0
    started_at: datetime | None = None
    updated_at: datetime | None = None
    finished_at: datetime | None = None
    message: str | None = None
    events: list[ResearchEvent] = Field(default_factory=list)


class ResearchState(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    investigation_id: UUID
    status: str
    progress: float
    research_mode: str | None
    research_progress: ResearchProgress | None
    error_message: str | None = None
