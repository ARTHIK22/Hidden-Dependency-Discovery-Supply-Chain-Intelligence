from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.database import get_db
from app.api.access import owned_investigation_ids
from app.api.dependencies import get_current_user
from app.models import Alert, Entity, Evidence, Investigation, Relationship, Risk
from app.models.user import User
from app.schemas.entity import EntityConnection, EntityDetail, EntityList, EntityRead

router = APIRouter(prefix="/entities", tags=["entities"])
search_router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=EntityList)
def list_entities(
    q: str | None = Query(default=None, max_length=160),
    entity_type: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntityList:
    query = select(Entity)
    count_query = select(func.count(Entity.id))
    if not current_user.is_admin:
        scope = Entity.investigation_id.in_(owned_investigation_ids(current_user))
        query = query.where(scope)
        count_query = count_query.where(scope)
    filters = []
    if q:
        term = f"%{q.strip().lower()}%"
        filters.append(func.lower(Entity.name).like(term))
    if entity_type:
        filters.append(func.lower(Entity.entity_type) == entity_type.strip().lower())
    if filters:
        condition = filters[0] if len(filters) == 1 else filters[0] & filters[1]
        query = query.where(condition)
        count_query = count_query.where(condition)
    items = db.scalars(query.order_by(Entity.name).limit(limit).offset(offset)).all()
    return EntityList(items=_entity_reads(db, items), total=db.scalar(count_query) or 0)


@router.get("/{entity_id}", response_model=EntityDetail)
def get_entity(entity_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> EntityDetail:
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    if not current_user.is_admin and entity.investigation_id not in set(db.scalars(owned_investigation_ids(current_user)).all()):
        raise HTTPException(status_code=404, detail="Entity not found")
    outgoing = db.execute(
        select(Relationship, Entity)
        .join(Entity, Entity.id == Relationship.target_entity_id)
        .where(Relationship.source_entity_id == entity_id)
    ).all()
    incoming = db.execute(
        select(Relationship, Entity)
        .join(Entity, Entity.id == Relationship.source_entity_id)
        .where(Relationship.target_entity_id == entity_id)
    ).all()
    if not current_user.is_admin:
        outgoing = [(relation, other) for relation, other in outgoing if relation.investigation_id == entity.investigation_id and other.investigation_id == entity.investigation_id]
        incoming = [(relation, other) for relation, other in incoming if relation.investigation_id == entity.investigation_id and other.investigation_id == entity.investigation_id]
    connections = [
        EntityConnection(
            id=relation.id,
            relationship_type=relation.relationship_type,
            direction="outgoing",
            entity_id=other.id,
            entity_name=other.name,
            confidence=relation.confidence,
            verification_status=relation.verification_status,
        )
        for relation, other in outgoing
    ] + [
        EntityConnection(
            id=relation.id,
            relationship_type=relation.relationship_type,
            direction="incoming",
            entity_id=other.id,
            entity_name=other.name,
            confidence=relation.confidence,
            verification_status=relation.verification_status,
        )
        for relation, other in incoming
    ]
    return EntityDetail(**_entity_reads(db, [entity])[0].model_dump(), connections=connections)


@search_router.get("")
def search_workspace(
    q: str = Query(min_length=2, max_length=160),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, list[dict[str, str]]]:
    term = f"%{q.strip().lower()}%"
    per_type = max(1, limit // 6)
    accessible = owned_investigation_ids(current_user)
    entity_query = select(Entity).where(func.lower(Entity.name).like(term))
    investigation_query = select(Investigation)
    if not current_user.is_admin:
        entity_query = entity_query.where(Entity.investigation_id.in_(accessible))
        investigation_query = investigation_query.where(Investigation.id.in_(accessible))
    entities = db.scalars(entity_query.order_by(Entity.name).limit(per_type)).all()
    investigations = db.scalars(
        investigation_query.where(or_(
            func.lower(Investigation.name).like(term), func.lower(Investigation.goal).like(term)
        )).order_by(Investigation.created_at.desc()).limit(per_type)
    ).all()
    source_entity = aliased(Entity)
    target_entity = aliased(Entity)
    relationship_query = (
        select(Relationship, source_entity, target_entity)
        .join(source_entity, source_entity.id == Relationship.source_entity_id)
        .join(target_entity, target_entity.id == Relationship.target_entity_id)
        .where(or_(
            func.lower(Relationship.relationship_type).like(term),
            func.lower(source_entity.name).like(term),
            func.lower(target_entity.name).like(term),
        ))
    )
    evidence_query = select(Evidence).where(or_(
        func.lower(Evidence.title).like(term), func.lower(Evidence.source).like(term), func.lower(Evidence.excerpt).like(term)
    ))
    risk_query = select(Risk, Entity).join(Entity, Entity.id == Risk.entity_id).where(or_(
        func.lower(Entity.name).like(term), func.lower(Risk.title).like(term), func.lower(Risk.reason).like(term)
    ))
    alert_query = select(Alert).where(or_(func.lower(Alert.title).like(term), func.lower(Alert.message).like(term)))
    if not current_user.is_admin:
        relationship_query = relationship_query.where(Relationship.investigation_id.in_(accessible))
        evidence_query = evidence_query.where(or_(
            Evidence.investigation_id.in_(accessible),
            and_(Evidence.investigation_id.is_(None), Evidence.relationship_id.in_(select(Relationship.id).where(Relationship.investigation_id.in_(accessible)))),
        ))
        risk_query = risk_query.where(Risk.investigation_id.in_(accessible))
        alert_query = alert_query.where(or_(
            and_(Alert.owner_id == current_user.id, Alert.investigation_id.in_(accessible)),
            and_(Alert.owner_id.is_(None), Alert.investigation_id.in_(select(Investigation.id).where(Investigation.demo_mode.is_(True)))),
        ))
    relationships = db.execute(relationship_query.order_by(Relationship.created_at.desc()).limit(per_type)).all()
    evidence_rows = db.scalars(evidence_query.order_by(Evidence.captured_at.desc()).limit(per_type)).all()
    risks = db.execute(risk_query.order_by(Risk.created_at.desc()).limit(per_type)).all()
    alerts = db.scalars(alert_query.order_by(Alert.created_at.desc()).limit(per_type)).all()
    return {
        "items": [
            {"id": str(item.id), "type": "entity", "label": item.name, "path": "/entities"}
            for item in entities
        ]
        + [
            {
                "id": str(item.id),
                "type": "investigation",
                "label": item.name,
                "path": "/investigations/" + str(item.id),
            }
            for item in investigations
        ]
        + [
            {"id": str(row.id), "type": "relationship", "label": f"{source.name} {row.relationship_type} {target.name}", "path": "/graph"}
            for row, source, target in relationships
        ]
        + [
            {"id": str(item.id), "type": "evidence", "label": item.title, "path": "/evidence"}
            for item in evidence_rows
        ]
        + [
            {"id": str(risk.id), "type": "risk", "label": f"{entity.name}: {risk.title}", "path": "/risks"}
            for risk, entity in risks
        ]
        + [
            {"id": str(item.id), "type": "alert", "label": item.title, "path": "/alerts"}
            for item in alerts
        ]
    }


def _entity_reads(db: Session, entities: list[Entity]) -> list[EntityRead]:
    canonical_ids: set[UUID] = set()
    evidence_ids: set[UUID] = set()
    canonical_by_entity: dict[UUID, UUID | None] = {}
    evidence_ids_by_entity: dict[UUID, list[UUID]] = {}
    for entity in entities:
        metadata = entity.metadata_json or {}
        try:
            canonical_id = UUID(str(metadata.get("canonical_entity_id"))) if metadata.get("canonical_entity_id") else None
        except ValueError:
            canonical_id = None
        canonical_by_entity[entity.id] = canonical_id
        if canonical_id is not None and entity.investigation_id is not None:
            canonical_ids.add(canonical_id)
        if not (metadata.get("sources") or []):
            parsed_ids = []
            for value in metadata.get("source_evidence_ids") or []:
                try:
                    parsed_ids.append(UUID(str(value)))
                except ValueError:
                    continue
            evidence_ids_by_entity[entity.id] = parsed_ids
            evidence_ids.update(parsed_ids)

    canonical_names: dict[tuple[UUID | None, UUID], str] = {}
    if canonical_ids:
        rows = db.execute(
            select(Entity.id, Entity.investigation_id, Entity.name).where(Entity.id.in_(canonical_ids))
        ).all()
        canonical_names = {(row.investigation_id, row.id): row.name for row in rows}

    evidence_by_id: dict[UUID, Evidence] = {}
    relationship_investigation: dict[UUID, UUID | None] = {}
    if evidence_ids:
        evidence_rows = db.scalars(select(Evidence).where(Evidence.id.in_(evidence_ids))).all()
        evidence_by_id = {row.id: row for row in evidence_rows}
        relationship_ids = {row.relationship_id for row in evidence_rows if row.relationship_id is not None}
        if relationship_ids:
            relation_rows = db.execute(
                select(Relationship.id, Relationship.investigation_id).where(Relationship.id.in_(relationship_ids))
            ).all()
            relationship_investigation = {row.id: row.investigation_id for row in relation_rows}

    result = []
    for entity in entities:
        data = EntityRead.model_validate(entity).model_dump()
        metadata = entity.metadata_json or {}
        resolution = metadata.get("resolution") or {}
        canonical_id = canonical_by_entity[entity.id]
        canonical_name = entity.name
        if canonical_id is not None and entity.investigation_id is not None:
            canonical_name = canonical_names.get((entity.investigation_id, canonical_id), entity.name)
        sources = metadata.get("sources") or []
        if not sources:
            sources = sorted({
                row.source
                for evidence_id in evidence_ids_by_entity.get(entity.id, [])
                if (row := evidence_by_id.get(evidence_id)) is not None
                and (
                    entity.investigation_id is None
                    or row.investigation_id == entity.investigation_id
                    or (
                        row.investigation_id is None
                        and row.relationship_id is not None
                        and relationship_investigation.get(row.relationship_id) == entity.investigation_id
                    )
                )
            })
        data.update({
            "normalized_name": metadata.get("normalized_name"),
            "aliases": metadata.get("aliases") or [],
            "canonical_entity_id": canonical_id,
            "canonical_entity_name": canonical_name,
            "resolution_status": metadata.get("resolution_status") or resolution.get("status"),
            "resolution_confidence": metadata.get("resolution_confidence", resolution.get("confidence")),
            "evidence_count": len(metadata.get("source_evidence_ids") or []),
            "sources": sources,
        })
        result.append(EntityRead(**data))
    return result
