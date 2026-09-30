from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InvestigationCreate(BaseModel):
    name: str | None = Field(default=None, max_length=240)
    goal: str = Field(min_length=20, max_length=10000)
    depth: Literal["standard", "deep", "maximum"] = "deep"
    scope_geography: bool = True
    scope_materials: bool = True
    scope_manufacturers: bool = True
    scope_verification: bool = True


class InvestigationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    goal: str
    status: str
    progress: float
    scope: dict[str, bool]
    depth: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class InvestigationList(BaseModel):
    items: list[InvestigationRead]
    total: int


class InvestigationCreated(BaseModel):
    investigation: InvestigationRead


class InvestigationDetail(InvestigationRead):
    entities_count: int = 0
    relationships_count: int = 0
    risk_count: int = 0
    timeline: list[dict[str, str | datetime]] = Field(default_factory=list)
