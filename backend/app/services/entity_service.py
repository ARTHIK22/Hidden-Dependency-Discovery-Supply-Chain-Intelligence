from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.entity_alias import EntityAlias


def list_entities(db: Session, query: str | None = None, limit: int = 100, offset: int = 0) -> list[Entity]:
    stmt = select(Entity).order_by(Entity.name).limit(limit).offset(offset)
    if query:
        term = f"%{query.strip()}%"
        alias_match = select(EntityAlias.entity_id).where(EntityAlias.alias.ilike(term))
        stmt = stmt.where(or_(Entity.name.ilike(term), Entity.legal_name.ilike(term), Entity.registration_number.ilike(term), Entity.id.in_(alias_match)))
    return list(db.scalars(stmt))


def find_entity(db: Session, entity_id: UUID) -> Entity | None:
    return db.get(Entity, entity_id)


def add_alias(db: Session, entity: Entity, alias: str, alias_type: str) -> EntityAlias:
    normalized = alias.strip()
    if not normalized:
        raise ValueError("Alias cannot be empty")
    match = db.scalar(select(EntityAlias).where(EntityAlias.alias.ilike(normalized)))
    if match and match.entity_id != entity.id:
        raise ValueError("Alias is already assigned to another entity")
    if match:
        return match
    item = EntityAlias(entity_id=entity.id, alias=normalized, alias_type=alias_type)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
