from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.entity_alias import EntityAlias
from resolution.canonicalizer import canonicalize_name
from resolution.similarity import name_similarity


def rank_entity_candidates(name: str, entities: list[Entity], aliases: dict[str, list[str]] | None = None, *, registration_number: str | None = None, country: str | None = None, website: str | None = None) -> list[dict]:
    aliases = aliases or {}
    normalized = canonicalize_name(name)
    requested_registration = (registration_number or "").strip().casefold()
    requested_domain = (website or "").strip().casefold().removeprefix("https://").removeprefix("http://").split("/")[0]
    candidates = []
    for entity in entities:
        score = name_similarity(name, entity.canonical_name or entity.name)
        reasons = ["normalized name similarity"]
        entity_registration = (entity.registration_number or "").strip().casefold()
        entity_domain = (entity.website or "").strip().casefold().removeprefix("https://").removeprefix("http://").split("/")[0]
        alias_match = any(canonicalize_name(alias) == normalized for alias in aliases.get(str(entity.id), []))
        if requested_registration and entity_registration == requested_registration:
            score, reasons = 1.0, ["registration identifier match"]
        elif requested_domain and requested_domain == entity_domain:
            score, reasons = max(score, 0.95), ["website domain match", *reasons]
        elif alias_match:
            score, reasons = max(score, 0.95), ["stored alias match", *reasons]
        elif country and entity.country and country.casefold() == entity.country.casefold():
            score = min(1.0, score + 0.05)
            reasons.append("country matches")
        elif country and entity.country and country.casefold() != entity.country.casefold():
            score = max(0.0, score - 0.15)
            reasons.append("country differs")
        if score >= 0.9:
            status = "MATCH"
        elif score >= 0.7:
            status = "POSSIBLE_MATCH"
        else:
            status = "NO_MATCH"
        candidates.append({"entity_id": entity.id, "name": entity.name, "score": round(score, 4), "status": status, "reasons": reasons})
    return sorted(candidates, key=lambda item: (-item["score"], str(item["entity_id"])))


def resolve_entity(db: Session, name: str, **signals) -> dict:
    entities = list(db.scalars(select(Entity)))
    alias_rows = list(db.scalars(select(EntityAlias)))
    aliases: dict[str, list[str]] = {}
    for alias in alias_rows:
        aliases.setdefault(str(alias.entity_id), []).append(alias.alias)
    candidates = rank_entity_candidates(name, entities, aliases, **signals)
    best = candidates[0] if candidates else None
    return {"best_match": best if best and best["status"] != "NO_MATCH" else None, "candidates": candidates, "auto_merge": False}
