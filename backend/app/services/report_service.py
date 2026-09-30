from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.relationship import Relationship
from app.models.risk import Risk
from app.models.source import Source


def build_report(db: Session, investigation: Investigation) -> dict:
    evidence = list(db.scalars(select(Evidence).where(Evidence.investigation_id == investigation.id)))
    relationships = list(db.scalars(select(Relationship).join(Evidence, Evidence.relationship_id == Relationship.id).where(Evidence.investigation_id == investigation.id).distinct()))
    risks = list(db.scalars(select(Risk).where(Risk.investigation_id == investigation.id)))
    source_ids = {e.source_id for e in evidence if e.source_id}
    sources = list(db.scalars(select(Source).where(Source.id.in_(source_ids)))) if source_ids else []
    entity_ids = {identity for relationship in relationships for identity in (relationship.source_entity_id, relationship.target_entity_id)}
    from app.models.entity import Entity
    entities = list(db.scalars(select(Entity).where(Entity.id.in_(entity_ids)))) if entity_ids else []
    return {
        "investigation": {
            "id": str(investigation.id), "name": investigation.name,
            "target": investigation.target, "description": investigation.description,
            "status": investigation.status, "priority": investigation.priority,
        },
        "entities": [{"id": str(e.id), "name": e.name, "entity_type": e.entity_type} for e in entities],
        "relationships": [{"id": str(r.id), "source_entity_id": str(r.source_entity_id), "target_entity_id": str(r.target_entity_id), "type": r.relationship_type, "confidence": r.confidence_score, "verification_status": r.verification_status} for r in relationships],
        "evidence": [{"id": str(e.id), "title": e.title, "source_id": str(e.source_id) if e.source_id else None, "confidence": e.confidence_score, "url": e.url, "published_at": e.published_at.isoformat() if e.published_at else None} for e in evidence],
        "sources": [{"id": str(source.id), "name": source.name, "source_type": source.source_type, "reliability_score": source.reliability_score} for source in sources],
        "risks": [{"id": str(r.id), "category": r.risk_type, "severity": r.severity, "score": r.score, "title": r.title, "description": r.description} for r in risks],
        "finding_count": len(relationships), "evidence_count": len(evidence),
        "confidence": (sum(e.confidence_score for e in evidence if e.confidence_score is not None) / len([e for e in evidence if e.confidence_score is not None])) if any(e.confidence_score is not None for e in evidence) else None,
        "contradictions": [],
    }
