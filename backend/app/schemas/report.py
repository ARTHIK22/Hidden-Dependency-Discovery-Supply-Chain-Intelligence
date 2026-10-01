from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportCreate(BaseModel):
    investigation_id: UUID


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    title: str
    content: str
    structured_content: dict[str, object] | None = None
    created_at: datetime


class ReportList(BaseModel):
    items: list[ReportRead]
    total: int
