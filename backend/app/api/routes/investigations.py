from fastapi import APIRouter

from app.schemas.investigation import InvestigationCreate
from app.services.investigation_service import InvestigationService

router = APIRouter(prefix="/investigations", tags=["Investigations"])


@router.post("/")
async def create_investigation(payload: InvestigationCreate):
    investigation = InvestigationService.create(payload)
    return {
        "success": True,
        "message": "Investigation created",
        "investigation": investigation,
    }


@router.get("/{investigation_id}")
async def get_investigation(investigation_id: str):
    return {
        "id": investigation_id,
        "status": "queued",
        "message": "Investigation lookup endpoint ready",
    }
