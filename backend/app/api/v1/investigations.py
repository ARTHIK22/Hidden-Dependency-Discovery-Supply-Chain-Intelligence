from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.investigation import Investigation
from app.models.investigation_step import InvestigationStep
from app.models.user import User
from app.schemas.investigation import InvestigationCreate, InvestigationRead, InvestigationStepRead, InvestigationUpdate
from orchestration.investigation_engine import run_investigation

router = APIRouter(prefix="/investigations", tags=["Investigations"])
ALLOWED_TRANSITIONS = {"draft": {"running", "archived"}, "running": {"paused", "completed", "failed"}, "paused": {"running", "archived"}, "failed": {"running", "archived"}, "completed": {"archived"}, "archived": set()}


@router.post("", response_model=InvestigationRead, status_code=201, summary="Create an investigation")
def create_investigation(payload: InvestigationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    investigation = Investigation(**payload.model_dump(), created_by=user.id)
    db.add(investigation)
    db.flush()
    db.add(AuditLog(user_id=user.id, action="investigation_created", resource_type="investigation", resource_id=str(investigation.id), metadata_json={}))
    db.commit()
    db.refresh(investigation)
    return investigation


@router.get("", response_model=list[InvestigationRead], summary="List investigations owned by the user")
def list_investigations(status_filter: str | None = Query(None, alias="status"), limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Investigation).where(Investigation.created_by == user.id).order_by(Investigation.updated_at.desc()).limit(limit).offset(offset)
    if status_filter:
        stmt = stmt.where(Investigation.status == status_filter)
    return list(db.scalars(stmt))


def owned_investigation(db: Session, user: User, investigation_id: UUID) -> Investigation:
    investigation = db.get(Investigation, investigation_id)
    if investigation is None or (investigation.created_by != user.id and not user.is_admin):
        raise HTTPException(404, "Investigation not found")
    return investigation


@router.get("/{investigation_id}", response_model=InvestigationRead, summary="Get an investigation")
def get_investigation(investigation_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return owned_investigation(db, user, investigation_id)


@router.get("/{investigation_id}/steps", response_model=list[InvestigationStepRead], summary="Get the investigation timeline")
def list_investigation_steps(investigation_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_investigation(db, user, investigation_id)
    return list(db.scalars(
        select(InvestigationStep)
        .where(InvestigationStep.investigation_id == investigation_id)
        .order_by(InvestigationStep.sequence)
    ))


@router.patch("/{investigation_id}", response_model=InvestigationRead, summary="Update an investigation")
def update_investigation(investigation_id: UUID, payload: InvestigationUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = owned_investigation(db, user, investigation_id)
    values = payload.model_dump(exclude_unset=True)
    if "status" in values and values["status"] != item.status and values["status"] not in ALLOWED_TRANSITIONS[item.status]:
        raise HTTPException(409, f"Invalid status transition: {item.status} to {values['status']}")
    for key, value in values.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{investigation_id}/start", response_model=InvestigationRead, summary="Start an investigation")
@router.post("/{investigation_id}/resume", response_model=InvestigationRead, summary="Resume an investigation")
def start_investigation(investigation_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = owned_investigation(db, user, investigation_id)
    if "running" not in ALLOWED_TRANSITIONS[item.status]:
        raise HTTPException(409, f"Cannot start an investigation in {item.status} state")
    item.status = "running"
    db.add(AuditLog(user_id=user.id, action="investigation_started", resource_type="investigation", resource_id=str(item.id), metadata_json={}))
    db.commit()
    run_investigation(db, item)
    db.refresh(item)
    return item


@router.post("/{investigation_id}/pause", response_model=InvestigationRead, summary="Pause an investigation")
def pause_investigation(investigation_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = owned_investigation(db, user, investigation_id)
    if item.status != "running":
        raise HTTPException(409, "Only a running investigation can be paused")
    item.status = "paused"
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{investigation_id}", status_code=204, summary="Archive an investigation")
def archive_investigation(investigation_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = owned_investigation(db, user, investigation_id)
    item.status = "archived"
    db.commit()
