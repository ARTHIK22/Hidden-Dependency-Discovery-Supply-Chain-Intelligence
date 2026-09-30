from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Entity, Evidence, Relationship

router = APIRouter(prefix="/graph", tags=["graph"])

_COLUMN_ORDER = {
    "company": 0,
    "supplier": 1,
    "manufacturer": 2,
    "material": 3,
    "facility": 4,
    "region": 5,
}


@router.get("")
def get_graph(db: Session = Depends(get_db)) -> dict[str, list[dict[str, object]]]:
    entities = db.scalars(select(Entity).order_by(Entity.created_at, Entity.name)).all()
    relationships = db.scalars(select(Relationship).order_by(Relationship.created_at)).all()
    entity_ids = {entity.id for entity in entities}
    evidence_rows = db.scalars(select(Evidence).order_by(Evidence.captured_at.desc())).all()
    evidence_by_relationship: dict[object, Evidence] = {}
    for evidence in evidence_rows:
        if evidence.relationship_id is not None:
            evidence_by_relationship.setdefault(evidence.relationship_id, evidence)

    row_by_type: dict[str, int] = defaultdict(int)
    nodes: list[dict[str, object]] = []
    for entity in entities:
        node_type = entity.entity_type.lower()
        column = _COLUMN_ORDER.get(node_type, 2)
        row = row_by_type[node_type]
        row_by_type[node_type] += 1
        nodes.append(
            {
                "id": str(entity.id),
                "type": "entity",
                "position": {"x": 80 + column * 230, "y": 120 + row * 150},
                "data": {
                    "label": entity.name,
                    "type": node_type,
                    "risk": entity.risk_score or 0,
                    "status": entity.risk_level or "Unassessed",
                    "entityId": str(entity.id),
                },
            }
        )

    edges: list[dict[str, object]] = []
    for relation in relationships:
        if relation.source_entity_id not in entity_ids or relation.target_entity_id not in entity_ids:
            continue
        evidence = evidence_by_relationship.get(relation.id)
        edges.append(
            {
                "id": str(relation.id),
                "source": str(relation.source_entity_id),
                "target": str(relation.target_entity_id),
                "label": relation.relationship_type,
                "data": {
                    "relationshipId": str(relation.id),
                    "relationshipType": relation.relationship_type,
                    "confidence": relation.confidence,
                    "source": evidence.source if evidence else relation.source,
                    "evidence": evidence.excerpt if evidence else relation.evidence_summary,
                    "verificationStatus": evidence.verification_status if evidence else relation.verification_status,
                },
            }
        )
    return {"nodes": nodes, "edges": edges}
