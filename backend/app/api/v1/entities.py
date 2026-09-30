from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.entity import Entity
from app.models.entity_alias import EntityAlias
from app.models.user import User
from app.schemas.entity import AliasCreate, EntityCreate, EntityRead, EntityUpdate
from app.services.entity_service import add_alias, list_entities

router = APIRouter(prefix="/entities", tags=["Entities"])


@router.post("", response_model=EntityRead, status_code=status.HTTP_201_CREATED, summary="Create an entity")
def create_entity(payload: EntityCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    values = payload.model_dump(exclude={"canonical_name"})
    canonical_name = (payload.canonical_name or payload.name).strip()
    entity = Entity(**values, canonical_name=canonical_name)
    db.add(entity)
    db.flush()
    if canonical_name.casefold() != payload.name.strip().casefold():
        db.add(EntityAlias(entity_id=entity.id, alias=payload.canonical_name.strip(), alias_type="canonical"))
    db.add(AuditLog(user_id=user.id, action="entity_created", resource_type="entity", resource_id=str(entity.id), metadata_json={}))
    db.commit()
    db.refresh(entity)
    return entity


@router.get("", response_model=list[EntityRead], summary="List and search entities")
def get_entities(q: str | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list_entities(db, q, limit, offset)


@router.get("/{entity_id}", response_model=EntityRead, summary="Get an entity")
def get_entity(entity_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(404, "Entity not found")
    return entity


@router.patch("/{entity_id}", response_model=EntityRead, summary="Update an entity")
def update_entity(entity_id: UUID, payload: EntityUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(404, "Entity not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(entity, key, value)
    db.add(AuditLog(user_id=user.id, action="entity_updated", resource_type="entity", resource_id=str(entity.id), metadata_json={}))
    db.commit()
    db.refresh(entity)
    return entity


@router.post("/{entity_id}/aliases", status_code=201, summary="Add an entity alias")
def create_alias(entity_id: UUID, payload: AliasCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(404, "Entity not found")
    try:
        alias = add_alias(db, entity, payload.alias, payload.alias_type)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"id": alias.id, "entity_id": alias.entity_id, "alias": alias.alias, "alias_type": alias.alias_type}


@router.get("/{entity_id}/aliases", summary="List entity aliases")
def get_aliases(entity_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if db.get(Entity, entity_id) is None:
        raise HTTPException(404, "Entity not found")
    return list(db.scalars(select(EntityAlias).where(EntityAlias.entity_id == entity_id).order_by(EntityAlias.alias)))
