from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.entity import Entity
from app.models.relationship import Relationship
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.source import Source
from app.models.user import User
from app.schemas.relationship import RelationshipCreate, RelationshipRead, RelationshipVerificationRead
from verification.relationship_verifier import verify_relationship_claim

router = APIRouter(prefix="/relationships", tags=["Relationships"])


@router.post("", response_model=RelationshipRead, status_code=status.HTTP_201_CREATED, summary="Record a structured relationship")
def create_relationship(payload: RelationshipCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.source_entity_id == payload.target_entity_id:
        raise HTTPException(422, "A relationship must connect two distinct entities")
    for entity_id in (payload.source_entity_id, payload.target_entity_id):
        if db.get(Entity, entity_id) is None:
            raise HTTPException(404, f"Entity {entity_id} not found")
    duplicate = db.scalar(select(Relationship.id).where(
        Relationship.source_entity_id == payload.source_entity_id,
        Relationship.target_entity_id == payload.target_entity_id,
        Relationship.relationship_type == payload.relationship_type,
    ))
    if duplicate is not None:
        raise HTTPException(409, "This relationship already exists; attach additional evidence to the existing relationship")
    relation = Relationship(**payload.model_dump(), strength=payload.confidence_score)
    db.add(relation)
    db.flush()
    db.add(AuditLog(user_id=user.id, action="relationship_created", resource_type="relationship", resource_id=str(relation.id), metadata_json={}))
    db.commit()
    db.refresh(relation)
    return relation


@router.get("", response_model=list[RelationshipRead], summary="List relationships")
def list_relationships(entity_id: UUID | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(Relationship).order_by(Relationship.discovered_at.desc()).limit(limit).offset(offset)
    if entity_id:
        stmt = stmt.where(or_(Relationship.source_entity_id == entity_id, Relationship.target_entity_id == entity_id))
    return list(db.scalars(stmt))


@router.get("/{relationship_id}", response_model=RelationshipRead, summary="Get a relationship")
def get_relationship(relationship_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    relation = db.get(Relationship, relationship_id)
    if relation is None:
        raise HTTPException(404, "Relationship not found")
    return relation


@router.post("/{relationship_id}/verify", response_model=RelationshipVerificationRead, summary="Verify a relationship from its recorded evidence")
def verify_relationship(relationship_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    relation = db.get(Relationship, relationship_id)
    if relation is None:
        raise HTTPException(404, "Relationship not found")
    evidence_items = list(db.scalars(
        select(Evidence)
        .join(Investigation, Evidence.investigation_id == Investigation.id)
        .where(
            Evidence.relationship_id == relationship_id,
            or_(Investigation.created_by == user.id, user.is_admin),
        )
    ))
    if not evidence_items:
        raise HTTPException(409, "At least one evidence record is required before verification")
    source_ids = {item.source_id for item in evidence_items if item.source_id}
    sources = {source.id: source for source in db.scalars(select(Source).where(Source.id.in_(source_ids)))} if source_ids else {}
    verification = verify_relationship_claim(evidence_items, sources)
    relation.confidence_score = verification["confidence"]["score"]
    relation.verification_status = verification["status"]
    db.add(AuditLog(user_id=user.id, action="relationship_verification_attempted", resource_type="relationship", resource_id=str(relation.id), metadata_json={"result": verification["status"], "confidence": relation.confidence_score}))
    db.commit()
    db.refresh(relation)
    return {"relationship": RelationshipRead.model_validate(relation), "verification": verification}
