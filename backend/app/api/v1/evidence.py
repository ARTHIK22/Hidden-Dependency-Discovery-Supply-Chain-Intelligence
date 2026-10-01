from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.database import get_db
from app.api.access import owned_investigation_ids
from app.api.dependencies import get_current_user
from app.models import Entity, Evidence, Relationship
from app.models.user import User
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
        title=evidence.title,
        metadata=evidence.metadata_json or {},
        relationship_verification=(relation.metadata_json or {}).get("verification") if relation else None,
    )


@router.get("", response_model=EvidenceList)
def list_evidence(
    q: str | None = Query(default=None, max_length=160),
    relationship_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvidenceList:
    source_entity = aliased(Entity)
    target_entity = aliased(Entity)
    statement = (
        select(Evidence, Relationship, source_entity, target_entity)
        .outerjoin(Relationship, Relationship.id == Evidence.relationship_id)
        .outerjoin(source_entity, and_(source_entity.id == Relationship.source_entity_id, source_entity.investigation_id == Relationship.investigation_id))
        .outerjoin(target_entity, and_(target_entity.id == Relationship.target_entity_id, target_entity.investigation_id == Relationship.investigation_id))
    )
    count_statement = select(func.count(Evidence.id)).outerjoin(
        Relationship, Relationship.id == Evidence.relationship_id
    )
    if not current_user.is_admin:
        accessible = owned_investigation_ids(current_user)
        accessible_relationships = select(Relationship.id).where(Relationship.investigation_id.in_(accessible))
        scope = or_(
            Evidence.investigation_id.in_(accessible),
            and_(Evidence.investigation_id.is_(None), Evidence.relationship_id.in_(accessible_relationships)),
        )
        statement = statement.where(scope)
        count_statement = count_statement.where(scope)
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
            source_entity, and_(source_entity.id == Relationship.source_entity_id, source_entity.investigation_id == Relationship.investigation_id)
        ).outerjoin(target_entity, and_(target_entity.id == Relationship.target_entity_id, target_entity.investigation_id == Relationship.investigation_id)).where(condition)
    rows = db.execute(statement.order_by(Evidence.captured_at.desc()).limit(limit).offset(offset)).all()
    return EvidenceList(
        items=[_evidence_read(*row) for row in rows],
        total=db.scalar(count_statement) or 0,
    )


@router.get("/{evidence_id}", response_model=EvidenceRead)
def get_evidence(evidence_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> EvidenceRead:
    source_entity = aliased(Entity)
    target_entity = aliased(Entity)
    row = db.execute(
        select(Evidence, Relationship, source_entity, target_entity)
        .outerjoin(Relationship, Relationship.id == Evidence.relationship_id)
        .outerjoin(source_entity, and_(source_entity.id == Relationship.source_entity_id, source_entity.investigation_id == Relationship.investigation_id))
        .outerjoin(target_entity, and_(target_entity.id == Relationship.target_entity_id, target_entity.investigation_id == Relationship.investigation_id))
        .where(Evidence.id == evidence_id)
    ).one_or_none()
    if row is not None and not current_user.is_admin:
        allowed_ids = set(db.scalars(owned_investigation_ids(current_user)).all())
        if row[0].investigation_id not in allowed_ids and not (
            row[0].investigation_id is None and row[1] is not None and row[1].investigation_id in allowed_ids
        ):
            row = None
    if row is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return _evidence_read(*row)
