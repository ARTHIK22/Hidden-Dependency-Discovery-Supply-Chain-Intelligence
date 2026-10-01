from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VerificationState(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    investigation_id: UUID
    status: str
    progress: float
    verification_mode: str | None = None
    verification_progress: dict[str, object] | None = None
    error_message: str | None = None


class VerificationStartResponse(VerificationState):
    accepted_at: datetime
