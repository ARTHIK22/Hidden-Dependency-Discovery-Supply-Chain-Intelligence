from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Entity, Investigation, Relationship
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
) -> EntityList:
    query = select(Entity)
    count_query = select(func.count(Entity.id))
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
    return EntityList(items=items, total=db.scalar(count_query) or 0)


@router.get("/{entity_id}", response_model=EntityDetail)
def get_entity(entity_id: UUID, db: Session = Depends(get_db)) -> EntityDetail:
    entity = db.get(Entity, entity_id)
    if entity is None:
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
    return EntityDetail(**EntityRead.model_validate(entity).model_dump(), connections=connections)


@search_router.get("")
def search_workspace(
    q: str = Query(min_length=2, max_length=160),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, str]]]:
    term = f"%{q.strip().lower()}%"
    entities = db.scalars(
        select(Entity).where(func.lower(Entity.name).like(term)).order_by(Entity.name).limit(limit)
    ).all()
    investigations = db.scalars(
        select(Investigation)
        .where(
            or_(
                func.lower(Investigation.name).like(term),
                func.lower(Investigation.goal).like(term),
            )
        )
        .order_by(Investigation.created_at.desc())
        .limit(limit)
    ).all()
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
    }
