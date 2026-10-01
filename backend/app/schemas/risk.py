from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RiskFactorRead(BaseModel):
    key: str
    label: str
    status: str
    score: float | None
    explanation: str
    source: str | None = None
    evidence_ids: list[str] = []


class RiskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_id: UUID
    entity_name: str
    entity_type: str
    investigation_id: UUID | None
    relationship_id: UUID | None = None
    snapshot_id: UUID | None = None
    target_type: str = "entity"
    score: float | None
    local_score: float | None = None
    propagated_score: float | None = None
    level: str
    reason: str
    risk_factors: list[RiskFactorRead] = []
    demo_mode: bool = False
    created_at: datetime


class RiskList(BaseModel):
    items: list[RiskRead]
    total: int


class RiskAnalysisState(BaseModel):
    investigation_id: str
    status: str
    progress: float
    risk_progress: dict[str, object] | None = None
    risk_analysis: dict[str, object] | None = None
    error_message: str | None = None
