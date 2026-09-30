from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class InvestigationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target: str | None = Field(default=None, max_length=500)
    description: str | None = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class InvestigationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    target: str | None = Field(default=None, max_length=500)
    description: str | None = None
    priority: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    status: str | None = Field(default=None, pattern="^(draft|running|paused|completed|failed|archived)$")


class InvestigationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID | None
    created_by: UUID | None
    name: str
    target: str | None
    description: str | None
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime


class InvestigationStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sequence: int
    stage: str
    status: str
    input_data: dict
    output_data: dict
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
