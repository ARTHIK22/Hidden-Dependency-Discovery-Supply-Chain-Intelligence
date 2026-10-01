from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MonitoringEnableRequest(BaseModel):
    interval_minutes: int = Field(default=60, ge=15, le=10080)


class MonitoringState(BaseModel):
    investigation_id: UUID
    enabled: bool
    status: Literal[
        "MONITORING_ENABLED",
        "MONITORING_DISABLED",
        "MONITORING_RUNNING",
        "MONITORING_COMPLETED",
        "MONITORING_FAILED",
    ]
    interval_minutes: int
    max_autonomous_depth: int
    last_checked_at: datetime | None = None
    next_check_at: datetime | None = None
    last_error: str | None = None
    graph_version: str | None = None
    entity_count: int = 0
    relationship_count: int = 0
    evidence_count: int = 0
    last_run: dict[str, Any] | None = None


class MonitoringRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    previous_snapshot_id: UUID | None
    current_snapshot_id: UUID | None
    change_count: int
    decision_count: int
    result_json: dict[str, Any]
    error_message: str | None


class MonitoringRunAccepted(BaseModel):
    investigation_id: UUID
    run_id: UUID
    status: str
    message: str


class InvestigationChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    run_id: UUID
    change_type: str
    entity_id: UUID | None
    relationship_id: UUID | None
    before_value: dict[str, Any] | None
    after_value: dict[str, Any] | None
    evidence_ids: list[str]
    created_at: datetime


class AgentDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    run_id: UUID
    trigger_event: str
    decision: str
    reason: str
    entity_id: UUID | None
    relationship_id: UUID | None
    priority: str
    evidence_ids: list[str]
    status: str
    result: str | None
    followup_investigation_id: UUID | None
    created_at: datetime
