from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    source_type: str = Field(min_length=1, max_length=100)
    url: HttpUrl | None = None
    publisher: str | None = None
    description: str | None = None
    reliability_score: float = Field(default=0, ge=0, le=1)
    metadata_json: dict = Field(default_factory=dict)


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    source_type: str
    url: str | None
    publisher: str | None
    description: str | None
    reliability_score: float
    metadata_json: dict
