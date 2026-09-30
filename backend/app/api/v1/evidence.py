from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.database import get_db
from app.models import Entity, Evidence, Relationship
from app.schemas.evidence import EvidenceList, EvidenceRead

router = APIRouter(prefix="/evidence", tags=["evidence"])


def _evidence_read(
    evidence: Evidence,
    relation: Relationship | None,
    source_entity: Entity | None,
    target_entity: Entity | None,
) -> EvidenceRead:
    return EvidenceRead(
        id=evidence.id,
        relationship_id=evidence.relationship_id,
        relationship_type=relation.relationship_type if relation else None,
        source_entity_id=source_entity.id if source_entity else None,
        source_entity_name=source_entity.name if source_entity else None,
        target_entity_id=target_entity.id if target_entity else None,
        target_entity_name=target_entity.name if target_entity else None,
        source=evidence.source,
        source_type=evidence.source_type,
        published_date=evidence.published_date,
        captured_at=evidence.captured_at,
        confidence=evidence.confidence,
        verification_status=evidence.verification_status,
        excerpt=evidence.excerpt,
        source_url=evidence.source_url,
    )


@router.get("", response_model=EvidenceList)
def list_evidence(
    q: str | None = Query(default=None, max_length=160),
    relationship_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> EvidenceList:
    source_entity = aliased(Entity)
    target_entity = aliased(Entity)
    statement = (
        select(Evidence, Relationship, source_entity, target_entity)
        .outerjoin(Relationship, Relationship.id == Evidence.relationship_id)
        .outerjoin(source_entity, source_entity.id == Relationship.source_entity_id)
        .outerjoin(target_entity, target_entity.id == Relationship.target_entity_id)
    )
    count_statement = select(func.count(Evidence.id)).outerjoin(
        Relationship, Relationship.id == Evidence.relationship_id
    )
    if relationship_id:
        statement = statement.where(Evidence.relationship_id == relationship_id)
        count_statement = count_statement.where(Evidence.relationship_id == relationship_id)
    if q:
        term = f"%{q.strip().lower()}%"
        condition = (
            func.lower(Evidence.source).like(term)
            | func.lower(Evidence.source_type).like(term)
            | func.lower(Evidence.excerpt).like(term)
            | func.lower(Relationship.relationship_type).like(term)
            | func.lower(source_entity.name).like(term)
            | func.lower(target_entity.name).like(term)
        )
        statement = statement.where(condition)
        count_statement = count_statement.outerjoin(
            source_entity, source_entity.id == Relationship.source_entity_id
        ).outerjoin(target_entity, target_entity.id == Relationship.target_entity_id).where(condition)
    rows = db.execute(statement.order_by(Evidence.captured_at.desc()).limit(limit).offset(offset)).all()
    return EvidenceList(
        items=[_evidence_read(*row) for row in rows],
        total=db.scalar(count_statement) or 0,
    )


@router.get("/{evidence_id}", response_model=EvidenceRead)
def get_evidence(evidence_id: UUID, db: Session = Depends(get_db)) -> EvidenceRead:
    source_entity = aliased(Entity)
    target_entity = aliased(Entity)
    row = db.execute(
        select(Evidence, Relationship, source_entity, target_entity)
        .outerjoin(Relationship, Relationship.id == Evidence.relationship_id)
        .outerjoin(source_entity, source_entity.id == Relationship.source_entity_id)
        .outerjoin(target_entity, target_entity.id == Relationship.target_entity_id)
        .where(Evidence.id == evidence_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return _evidence_read(*row)
