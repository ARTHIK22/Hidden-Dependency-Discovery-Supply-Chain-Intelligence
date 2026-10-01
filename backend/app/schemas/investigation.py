from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agents.schemas import InvestigationPlan, PlannerMode


InvestigationStatus = Literal[
    "QUEUED",
    "PLANNING",
    "PLANNED",
    "RESEARCHING",
    "VERIFYING",
    "RESEARCH_COMPLETED",
    "VERIFICATION_COMPLETED",
    "RISK_ANALYZING",
    "RISK_ANALYZED",
    "COMPLETED",
    "FAILED",
    "draft",
    "queued",
    "running",
    "paused",
    "completed",
    "failed",
    "archived",
]


class InvestigationCreate(BaseModel):
    name: str | None = Field(default=None, max_length=240)
    goal: str = Field(min_length=20, max_length=10000)
    depth: Literal["standard", "deep", "maximum"] = "deep"
    scope_geography: bool = True
    scope_materials: bool = True
    scope_manufacturers: bool = True
    scope_verification: bool = True

    @field_validator("goal", mode="before")
    @classmethod
    def trim_goal(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class InvestigationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    goal: str
    status: InvestigationStatus
    progress: float
    scope: dict[str, bool]
    depth: str
    objective: str | None = None
    plan: InvestigationPlan | None = None
    planner_mode: PlannerMode | None = None
    research_mode: str | None = None
    research_progress: dict[str, object] | None = None
    verification_mode: str | None = None
    verification_progress: dict[str, object] | None = None
    risk_progress: dict[str, object] | None = None
    risk_analysis: dict[str, object] | None = None
    autonomous_context: dict[str, object] | None = None
    lifecycle_events: list[dict[str, object]] = Field(default_factory=list)
    demo_mode: bool = False
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class InvestigationList(BaseModel):
    items: list[InvestigationRead]
    total: int


class InvestigationCreated(BaseModel):
    investigation: InvestigationRead
    plan: InvestigationPlan


class InvestigationPlanResponse(InvestigationPlan):
    pass


class InvestigationDetail(InvestigationRead):
    entities_count: int = 0
    relationships_count: int = 0
    evidence_count: int = 0
    risk_count: int = 0
    timeline: list[dict[str, Any]] = Field(default_factory=list)
