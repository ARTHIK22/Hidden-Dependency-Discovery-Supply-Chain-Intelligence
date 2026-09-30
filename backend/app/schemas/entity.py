from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class EntityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    entity_type: str = Field(min_length=1, max_length=100)
    canonical_name: str | None = Field(default=None, max_length=500)
    legal_name: str | None = Field(default=None, max_length=500)
    registration_number: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=100)
    website: str | None = Field(default=None, max_length=1000)
    description: str | None = None
    identifiers: dict[str, str] = Field(default_factory=dict)
    metadata_json: dict = Field(default_factory=dict)


class EntityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    entity_type: str | None = Field(default=None, min_length=1, max_length=100)
    legal_name: str | None = None
    canonical_name: str | None = None
    registration_number: str | None = None
    country: str | None = None
    website: str | None = None
    description: str | None = None
    identifiers: dict[str, str] | None = None
    metadata_json: dict | None = None
    status: str | None = None


class EntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    entity_type: str
    legal_name: str | None
    canonical_name: str | None
    registration_number: str | None
    country: str | None
    website: str | None
    description: str | None
    identifiers: dict[str, str]
    metadata_json: dict
    status: str
    created_at: datetime
    updated_at: datetime


class AliasCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=500)
    alias_type: str = Field(default="name", max_length=100)
