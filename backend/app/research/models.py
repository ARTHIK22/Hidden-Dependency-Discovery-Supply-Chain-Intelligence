from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ResearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(min_length=3, max_length=500)
    purpose: str = Field(min_length=1, max_length=1000)
    entity_focus: list[str] = Field(default_factory=list, max_length=16)
    relationship_focus: list[str] = Field(default_factory=list, max_length=16)
    depth: int = Field(ge=1, le=3)
    step_id: str = Field(min_length=1, max_length=80)


class ResearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(min_length=3, max_length=500)
    source_url: HttpUrl
    source_title: str = Field(min_length=1, max_length=500)
    source_domain: str = Field(min_length=1, max_length=253)
    retrieved_at: datetime
    content: str = Field(min_length=1, max_length=20000)
    relevance: float | None = Field(default=None, ge=0, le=1)
    research_step: str = Field(min_length=1, max_length=1000)
    provider: str = Field(min_length=1, max_length=120)
    source_type: str = Field(default="web", min_length=1, max_length=120)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ResearchBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    query: ResearchQuery
    results: list[ResearchResult] = Field(default_factory=list, max_length=20)


class ExtractedEntity(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=500)
    entity_type: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    source_evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    confidence: float = Field(ge=0, le=1)
    aliases: list[str] = Field(default_factory=list, max_length=20)


class ExtractedRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    source_entity: str = Field(min_length=1, max_length=500)
    target_entity: str = Field(min_length=1, max_length=500)
    relationship_type: str = Field(min_length=1, max_length=100)
    evidence_text: str = Field(min_length=1, max_length=4000)
    confidence: float = Field(ge=0, le=1)


ResearchMode = Literal["local_demo", "external"]
