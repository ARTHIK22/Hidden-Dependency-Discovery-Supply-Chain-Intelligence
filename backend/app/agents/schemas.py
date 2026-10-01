import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PlannerMode = Literal["local_demo", "llm"]


class InvestigationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    target: str | None
    normalized_goal: str = Field(min_length=1, max_length=10000)
    objective: str = Field(min_length=1, max_length=2000)
    depth: int = Field(ge=1, le=3)
    steps: list[str] = Field(min_length=1, max_length=12)
    research_questions: list[str] = Field(min_length=1, max_length=12)
    entity_types: list[str] = Field(min_length=1, max_length=16)
    relationship_types: list[str] = Field(min_length=1, max_length=16)
    verification_requirements: list[str] = Field(min_length=1, max_length=8)
    planner_mode: PlannerMode
    target_clarification: str | None = None

    @field_validator(
        "steps",
        "research_questions",
        "entity_types",
        "relationship_types",
        "verification_requirements",
    )
    @classmethod
    def require_non_empty_items(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("Plan lists cannot contain empty items")
        return values

    @field_validator("target")
    @classmethod
    def normalize_target(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"\s+", " ", value).strip(" ,.;:")
        return normalized or None