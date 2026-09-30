import hashlib
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.entity import Entity
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.relationship import Relationship
from app.models.source import Source
from app.models.user import User
from app.schemas.evidence import EvidenceCreate, EvidenceRead

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.post("", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED, summary="Record evidence with a content digest")
def create_evidence(payload: EvidenceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    for model, identity in ((Source, payload.source_id), (Entity, payload.entity_id), (Relationship, payload.relationship_id), (Investigation, payload.investigation_id)):
        if identity is not None and db.get(model, identity) is None:
            raise HTTPException(404, f"Referenced {model.__name__.lower()} not found")
    if payload.investigation_id is None:
        raise HTTPException(422, "Evidence must belong to an investigation")
    investigation = db.get(Investigation, payload.investigation_id)
    if investigation.created_by != user.id and not user.is_admin:
        raise HTTPException(404, "Investigation not found")
    values = payload.model_dump()
    if values.get("url") is not None:
        values["url"] = str(values["url"])
    item = Evidence(**values, content_hash=hashlib.sha256(payload.content.encode("utf-8")).hexdigest())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[EvidenceRead], summary="List evidence")
def list_evidence(relationship_id: UUID | None = None, entity_id: UUID | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Evidence).join(Investigation, Evidence.investigation_id == Investigation.id).where(
        or_(Investigation.created_by == user.id, user.is_admin)
    ).order_by(Evidence.collected_at.desc()).limit(limit).offset(offset)
    if relationship_id:
        stmt = stmt.where(Evidence.relationship_id == relationship_id)
    if entity_id:
        stmt = stmt.where(Evidence.entity_id == entity_id)
    return list(db.scalars(stmt))
