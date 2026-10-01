"""Owner-scoped watchlist access and CRUD operations."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.api.access import get_accessible_investigation, owned_investigation_ids
from app.models import Entity, Investigation, Relationship, Risk, WatchlistEntry
from app.models.user import User
from app.schemas.watchlist import WatchlistCreate, WatchlistList, WatchlistRead


def list_watchlist(db: Session, user: User, q: str | None = None) -> WatchlistList:
    entity = aliased(Entity)
    relation = aliased(Relationship)
    source = aliased(Entity)
    target = aliased(Entity)
    investigation = aliased(Investigation)
    statement = (
        select(WatchlistEntry, entity, relation, source, target, investigation)
        .outerjoin(entity, WatchlistEntry.entity_id == entity.id)
        .outerjoin(relation, WatchlistEntry.relationship_id == relation.id)
        .outerjoin(source, relation.source_entity_id == source.id)
        .outerjoin(target, relation.target_entity_id == target.id)
        .outerjoin(investigation, WatchlistEntry.investigation_id == investigation.id)
    )
    demo_entity_ids = select(Entity.id).join(Investigation, Investigation.id == Entity.investigation_id).where(Investigation.demo_mode.is_(True))
    demo_relationship_ids = select(Relationship.id).join(Investigation, Investigation.id == Relationship.investigation_id).where(Investigation.demo_mode.is_(True))
    if not user.is_admin:
        personal = WatchlistEntry.owner_id == user.id
        shared_demo = and_demo_entry(demo_entity_ids, demo_relationship_ids)
        statement = statement.where(or_(personal, shared_demo))
    if q:
        pattern = f"%{q.strip().lower()}%"
        statement = statement.where(or_(
            entity.name.ilike(pattern), source.name.ilike(pattern), target.name.ilike(pattern), investigation.name.ilike(pattern)
        ))
    rows = db.execute(statement.order_by(WatchlistEntry.created_at.desc(), WatchlistEntry.id)).all()
    relation_ids = {relation_row.id for _, _, relation_row, _, _, _ in rows if relation_row is not None}
    relation_risks: dict[UUID, Risk] = {}
    if relation_ids:
        for risk_row in db.scalars(
            select(Risk).where(Risk.relationship_id.in_(relation_ids)).order_by(Risk.created_at.desc(), Risk.id)
        ).all():
            if risk_row.relationship_id is not None:
                relation_risks.setdefault(risk_row.relationship_id, risk_row)
    items: list[WatchlistRead] = []
    for entry, entity_row, relation_row, source_row, target_row, investigation_row in rows:
        label = ""
        entity_type = entry.target_type
        score: float | None = None
        level: str | None = None
        if entity_row is not None:
            label = entity_row.name
            entity_type = entity_row.entity_type
            score, level = entity_row.risk_score, entity_row.risk_level
        elif relation_row is not None:
            label = f"{source_row.name if source_row else 'Unknown'} → {target_row.name if target_row else 'Unknown'}"
            entity_type = relation_row.relationship_type
            risk = relation_risks.get(relation_row.id)
            score, level = _score(risk), None if risk is None else risk.level
        elif investigation_row is not None:
            label = investigation_row.name
            entity_type = "investigation"
            summary = (investigation_row.risk_analysis or {}).get("summary", {})
            score, level = summary.get("overall_score"), summary.get("overall_level")
        else:
            label = "Risk condition"
            entity_type = "risk condition"
        items.append(WatchlistRead(
            id=entry.id, target_type=entry.target_type, target_id=entry.target_id,
            entity_id=entry.entity_id, relationship_id=entry.relationship_id,
            investigation_id=entry.investigation_id, status=entry.status, created_at=entry.created_at,
            entity_name=label, entity_type=entity_type, risk_score=score, risk_level=level,
            risk_threshold=entry.risk_threshold, condition_json=entry.condition_json or {},
            is_demo=entry.owner_id is None,
        ))
    return WatchlistList(items=items, total=len(items))


def add_watchlist_entry(db: Session, payload: WatchlistCreate, user: User) -> WatchlistRead:
    target_id = payload.target_id
    if target_id is None:
        raise HTTPException(status_code=422, detail="A watch target is required")
    entity: Entity | None = None
    relation: Relationship | None = None
    investigation: Investigation | None = None
    entity_id: UUID | None = None
    relationship_id: UUID | None = None
    investigation_id: UUID | None = None

    if payload.target_type == "entity":
        entity = _accessible_entity(db, target_id, user)
        entity_id = entity.id
        investigation_id = entity.investigation_id
        label, entity_type = entity.name, entity.entity_type
    elif payload.target_type == "relationship":
        relation = db.get(Relationship, target_id)
        if relation is None or relation.investigation_id is None:
            raise HTTPException(status_code=404, detail="Relationship not found")
        investigation = get_accessible_investigation(db, relation.investigation_id, user)
        relationship_id, investigation_id = relation.id, investigation.id
        source = db.get(Entity, relation.source_entity_id)
        target = db.get(Entity, relation.target_entity_id)
        label, entity_type = f"{source.name if source else 'Unknown'} → {target.name if target else 'Unknown'}", relation.relationship_type
    else:
        investigation = get_accessible_investigation(db, target_id, user)
        investigation_id = investigation.id
        label = investigation.name if payload.target_type == "investigation" else "Risk condition"
        entity_type = payload.target_type

    target_key = f"{payload.target_type}:{target_id}"
    existing = db.scalar(select(WatchlistEntry).where(WatchlistEntry.owner_id == user.id, WatchlistEntry.target_key == target_key))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Target is already on your watchlist")
    entry = WatchlistEntry(
        owner_id=user.id,
        entity_id=entity_id,
        relationship_id=relationship_id,
        investigation_id=investigation_id,
        target_type=payload.target_type,
        target_id=target_id,
        target_key=target_key,
        risk_threshold=payload.risk_threshold,
        condition_json=payload.condition_json,
    )
    db.add(entry)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Target is already on your watchlist") from exc
    db.refresh(entry)
    return WatchlistRead(
        id=entry.id, target_type=entry.target_type, target_id=entry.target_id,
        entity_id=entry.entity_id, relationship_id=entry.relationship_id, investigation_id=entry.investigation_id,
        status=entry.status, created_at=entry.created_at, entity_name=label, entity_type=entity_type,
        risk_score=None if entity is None else entity.risk_score,
        risk_level=None if entity is None else entity.risk_level,
        risk_threshold=entry.risk_threshold, condition_json=entry.condition_json or {}, is_demo=False,
    )


def remove_watchlist_entry(db: Session, entry_id: UUID, user: User) -> None:
    entry = db.scalar(select(WatchlistEntry).where(WatchlistEntry.id == entry_id, WatchlistEntry.owner_id == user.id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    db.delete(entry)
    db.commit()


def remove_entity_watch(db: Session, entity_id: UUID, user: User) -> None:
    entry = db.scalar(select(WatchlistEntry).where(
        WatchlistEntry.entity_id == entity_id,
        WatchlistEntry.owner_id == user.id,
    ))
    if entry is None:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    db.delete(entry)
    db.commit()


def _accessible_entity(db: Session, entity_id: UUID, user: User) -> Entity:
    entity = db.get(Entity, entity_id)
    if entity is None or entity.investigation_id is None:
        if user.is_admin and entity is not None:
            return entity
        raise HTTPException(status_code=404, detail="Entity not found")
    get_accessible_investigation(db, entity.investigation_id, user)
    return entity


def _score(risk: Risk | None) -> float | None:
    if risk is None or risk.score is None:
        return None
    return float(risk.score) if risk.score_scale == "percent" else float(risk.score) * 100.0


def and_demo_entry(entity_ids, relationship_ids):
    return and_(
        WatchlistEntry.owner_id.is_(None),
        or_(
            WatchlistEntry.entity_id.in_(entity_ids),
            WatchlistEntry.relationship_id.in_(relationship_ids),
            WatchlistEntry.investigation_id.in_(select(Investigation.id).where(Investigation.demo_mode.is_(True))),
        ),
    )
