from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class WorkflowEvent:
    investigation_id: str
    stage: str
    status: str
    detail: dict[str, Any]
    created_at: datetime


def make_event(investigation_id, stage: str, status: str, detail: dict | None = None) -> WorkflowEvent:
    return WorkflowEvent(str(investigation_id), stage, status, detail or {}, datetime.now(timezone.utc))
