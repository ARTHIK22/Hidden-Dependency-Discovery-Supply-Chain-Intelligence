from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity_alias import EntityAlias
from resolution.canonicalizer import canonicalize_name


def find_alias(db: Session, alias: str) -> EntityAlias | None:
    normalized = canonicalize_name(alias)
    if not normalized:
        return None
    return db.scalar(select(EntityAlias).where(EntityAlias.alias.ilike(alias.strip())))


def create_alias(db: Session, entity_id, alias: str, alias_type: str = "name") -> EntityAlias:
    cleaned = " ".join(alias.split())
    if not canonicalize_name(cleaned):
        raise ValueError("Alias must contain letters or numbers")
    existing = find_alias(db, cleaned)
    if existing and existing.entity_id != entity_id:
        raise ValueError("Alias already identifies another entity")
    if existing:
        return existing
    item = EntityAlias(entity_id=entity_id, alias=cleaned, alias_type=alias_type)
    db.add(item)
    db.flush()
    return item
