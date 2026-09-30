from enum import StrEnum


class InvestigationStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


TRANSITIONS = {
    InvestigationStatus.DRAFT: {InvestigationStatus.RUNNING, InvestigationStatus.ARCHIVED},
    InvestigationStatus.RUNNING: {InvestigationStatus.PAUSED, InvestigationStatus.COMPLETED, InvestigationStatus.FAILED},
    InvestigationStatus.PAUSED: {InvestigationStatus.RUNNING, InvestigationStatus.ARCHIVED},
    InvestigationStatus.FAILED: {InvestigationStatus.RUNNING, InvestigationStatus.ARCHIVED},
    InvestigationStatus.COMPLETED: {InvestigationStatus.ARCHIVED},
    InvestigationStatus.ARCHIVED: set(),
}


def can_transition(current: str, target: str) -> bool:
    try:
        return InvestigationStatus(target) in TRANSITIONS[InvestigationStatus(current)]
    except ValueError:
        return False
