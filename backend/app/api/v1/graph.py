from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.access import owned_investigation_ids
from app.api.dependencies import get_current_user
from app.models import Entity, Evidence, Investigation, Relationship, Risk
from app.models.user import User

router = APIRouter(prefix="/graph", tags=["graph"])

_COLUMN_ORDER = {
    "company": 0,
    "supplier": 1,
    "manufacturer": 2,
    "material": 3,
    "facility": 4,
    "region": 5,
}
_EVIDENCE_PREVIEW_PER_RELATIONSHIP = 3


@router.get("")
def get_graph(
    limit: int = Query(default=500, ge=25, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    entity_query = select(Entity).order_by(Entity.created_at.desc(), Entity.id).limit(limit + 1).offset(offset)
    if not current_user.is_admin:
        accessible = owned_investigation_ids(current_user)
        entity_query = entity_query.where(Entity.investigation_id.in_(accessible))
    entity_rows = db.scalars(entity_query).all()
    has_more_entities = len(entity_rows) > limit
    entities = entity_rows[:limit]
    entity_ids = {entity.id for entity in entities}
    relationship_query = (
        select(Relationship)
        .where(
            Relationship.source_entity_id.in_(entity_ids),
            Relationship.target_entity_id.in_(entity_ids),
        )
        .order_by(Relationship.created_at.desc(), Relationship.id)
        .limit(limit * 2 + 1)
    )
    if not current_user.is_admin:
        relationship_query = relationship_query.where(Relationship.investigation_id.in_(accessible))
    relationship_rows = db.scalars(relationship_query).all()
    has_more_relationships = len(relationship_rows) > limit * 2
    relationships = relationship_rows[:limit * 2]
    selected_investigation_ids = {entity.investigation_id for entity in entities if entity.investigation_id is not None}
    investigation_query = select(Investigation).where(Investigation.id.in_(selected_investigation_ids))
    visible_investigations = db.scalars(investigation_query).all()
    current_snapshot_ids = [
        str((item.risk_analysis or {}).get("snapshot_id"))
        for item in visible_investigations
        if (item.risk_analysis or {}).get("snapshot_id")
    ]
    relationship_ids = {relationship.id for relationship in relationships}
    relationship_risks: dict[object, Risk] = {}
    entity_risks: dict[object, Risk] = {}
    if current_snapshot_ids:
        risk_query = select(Risk).where(
            Risk.snapshot_id.in_(current_snapshot_ids),
            or_(Risk.entity_id.in_(entity_ids), Risk.relationship_id.in_(relationship_ids)),
        ).order_by(Risk.created_at.desc(), Risk.id)
        risk_rows = db.scalars(risk_query).all()
        for risk_row in risk_rows:
            if risk_row.relationship_id is None:
                entity_risks.setdefault(risk_row.entity_id, risk_row)
            if risk_row.relationship_id is not None:
                relationship_risks.setdefault(risk_row.relationship_id, risk_row)
    fallback_evidence_ids: set[UUID] = set()
    for relationship in relationships:
        verification = (relationship.metadata_json or {}).get("verification") or {}
        for value in (verification.get("evidence_ids") or [])[:_EVIDENCE_PREVIEW_PER_RELATIONSHIP]:
            try:
                fallback_evidence_ids.add(UUID(str(value)))
            except ValueError:
                continue
    ranked_evidence = (
        select(
            Evidence.id.label("evidence_id"),
            func.row_number().over(
                partition_by=Evidence.relationship_id,
                order_by=(Evidence.captured_at.desc(), Evidence.id),
            ).label("evidence_rank"),
        )
        .where(Evidence.relationship_id.in_(relationship_ids))
        .subquery()
    )
    preview_evidence_ids = select(ranked_evidence.c.evidence_id).where(
        ranked_evidence.c.evidence_rank <= _EVIDENCE_PREVIEW_PER_RELATIONSHIP
    )
    evidence_filter = Evidence.id.in_(preview_evidence_ids)
    if fallback_evidence_ids:
        evidence_filter = or_(evidence_filter, Evidence.id.in_(fallback_evidence_ids))
    evidence_query = select(Evidence).where(evidence_filter).order_by(Evidence.captured_at.desc(), Evidence.id)
    evidence_rows = db.scalars(evidence_query).all()
    evidence_count_rows = db.execute(
        select(Evidence.relationship_id, func.count(Evidence.id))
        .where(Evidence.relationship_id.in_(relationship_ids))
        .group_by(Evidence.relationship_id)
    ).all()
    linked_evidence_counts = {relationship_id: count for relationship_id, count in evidence_count_rows}
    evidence_by_relationship: dict[object, list[Evidence]] = defaultdict(list)
    evidence_by_id = {str(row.id): row for row in evidence_rows}
    for evidence in evidence_rows:
        if evidence.relationship_id is not None:
            evidence_by_relationship[evidence.relationship_id].append(evidence)

    canonical_id_by_entity = {}
    for entity in entities:
        metadata = entity.metadata_json or {}
        candidate = (metadata.get("resolution") or {}).get("canonical_entity_id") or metadata.get("canonical_entity_id")
        try:
            canonical_id_by_entity[entity.id] = UUID(str(candidate)) if candidate else entity.id
        except ValueError:
            canonical_id_by_entity[entity.id] = entity.id
    canonical_entities = {entity.id: entity for entity in entities if canonical_id_by_entity.get(entity.id) == entity.id}

    row_by_type: dict[str, int] = defaultdict(int)
    nodes: list[dict[str, object]] = []
    for entity in canonical_entities.values():
        node_type = entity.entity_type.lower()
        metadata = entity.metadata_json or {}
        demo_only = bool(metadata.get("demo_only")) or "DEMO" in (entity.description or "").upper()
        entity_risk = entity_risks.get(entity.id)
        risk_score = entity.risk_score if demo_only else (None if entity_risk is None else entity_risk.score)
        risk_level = entity.risk_level if demo_only else (None if entity_risk is None else entity_risk.level)
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
                    "risk": risk_score,
                    "riskLevel": risk_level,
                    "riskStatus": "DEMO_ONLY" if demo_only else ("UNKNOWN" if entity_risk is None or entity_risk.score is None else "ASSESSED"),
                    "riskReason": None if entity_risk is None else entity_risk.reason,
                    "riskFactors": [] if entity_risk is None else (entity_risk.risk_factors or []),
                    "propagatedRisk": None if entity_risk is None else entity_risk.propagated_score,
                    "status": risk_level or "UNKNOWN",
                    "entityId": str(entity.id),
                    "demoOnly": demo_only,
                    "researchMode": metadata.get("research_mode"),
                    "aliases": metadata.get("aliases") or [],
                    "resolutionStatus": (metadata.get("resolution") or {}).get("status") or metadata.get("resolution_status"),
                    "resolutionConfidence": (metadata.get("resolution") or {}).get("confidence") or metadata.get("resolution_confidence"),
                    "evidenceCount": len(metadata.get("source_evidence_ids") or []),
                },
            }
        )

    edges: list[dict[str, object]] = []
    edge_index_by_key: dict[tuple[str, str, str], int] = {}
    for relation in relationships:
        if relation.source_entity_id not in entity_ids or relation.target_entity_id not in entity_ids:
            continue
        source_id = canonical_id_by_entity.get(relation.source_entity_id, relation.source_entity_id)
        target_id = canonical_id_by_entity.get(relation.target_entity_id, relation.target_entity_id)
        if source_id == target_id or source_id not in canonical_entities or target_id not in canonical_entities:
            continue
        relation_evidence = evidence_by_relationship.get(relation.id, [])
        relationship_metadata = relation.metadata_json or {}
        verification = relationship_metadata.get("verification") or {}
        verification_evidence_ids = verification.get("evidence_ids", [])
        if not relation_evidence:
            relation_evidence = [evidence_by_id[str(value)] for value in verification_evidence_ids if str(value) in evidence_by_id]
        evidence = relation_evidence[0] if relation_evidence else None
        demo_only = (
            bool(relationship_metadata.get("demo_only"))
            or relation.verification_status == "demo_unverified"
        )
        edge_key = (str(source_id), str(target_id), relation.relationship_type.strip().upper())
        edge_data = {
                    "relationshipId": str(relationship_metadata.get("canonical_relationship_id") or relation.id),
                    "relationshipIds": list(verification.get("candidate_relationship_ids") or [str(relation.id)]),
                    "relationshipType": relation.relationship_type,
                    "confidence": verification.get("confidence", relation.confidence),
                    "source": evidence.source if evidence else relation.source,
                    "evidence": evidence.excerpt if evidence else relation.evidence_summary,
                    "verificationStatus": verification.get("status", relation.verification_status),
                    "evidenceCount": max(len(verification.get("evidence_ids", [])), linked_evidence_counts.get(relation.id, 0)),
                    "evidenceTruncated": max(len(verification.get("evidence_ids", [])), linked_evidence_counts.get(relation.id, 0)) > len(relation_evidence),
                    "sources": sorted({row.source for row in relation_evidence}),
                    "supportingEvidenceCount": len(verification.get("supporting_evidence_ids", [])),
                    "conflictingEvidenceCount": len(verification.get("conflicting_evidence_ids", [])),
                    "conflictFlag": bool(verification.get("conflicting_evidence_ids")),
                    "verifiedAt": verification.get("verified_at") or verification.get("evaluated_at"),
                    "verification": verification,
                    "evidenceItems": [
                        {
                            "id": str(row.id), "source": row.source, "sourceType": row.source_type,
                            "url": row.source_url, "title": row.title, "excerpt": row.excerpt,
                            "capturedAt": row.captured_at.isoformat() if row.captured_at else None,
                            "publishedDate": row.published_date.isoformat() if row.published_date else None,
                            "verificationStatus": row.verification_status,
                        }
                        for row in relation_evidence
                    ],
                    "demoOnly": demo_only,
                    "researchMode": relationship_metadata.get("research_mode"),
                    "riskScore": None,
                    "riskLevel": None,
                    "riskReason": None,
                    "riskFactors": [],
                }
        relation_risk = relationship_risks.get(relation.id)
        if relation_risk is not None:
            edge_data["riskScore"] = relation_risk.score if relation_risk.score_scale == "percent" else (None if relation_risk.score is None else relation_risk.score * 100.0)
            edge_data["riskLevel"] = relation_risk.level
            edge_data["riskReason"] = relation_risk.reason
            edge_data["riskFactors"] = relation_risk.risk_factors or []
        previous = edge_index_by_key.get(edge_key)
        if previous is not None:
            previous_data = edges[previous]["data"]
            previous_items = previous_data.get("evidenceItems", [])
            merged_items = {item["id"]: item for item in previous_items}
            merged_items.update({item["id"]: item for item in edge_data["evidenceItems"]})
            previous_data["evidenceItems"] = list(merged_items.values())
            previous_data["sources"] = sorted(set(previous_data.get("sources", [])) | set(edge_data["sources"]))
            previous_data["relationshipIds"] = sorted(set(previous_data.get("relationshipIds", [])) | set(edge_data["relationshipIds"]))
            previous_data["evidenceCount"] = max(int(previous_data.get("evidenceCount", 0)), len(merged_items))
            previous_data["evidenceTruncated"] = bool(previous_data.get("evidenceTruncated")) or bool(edge_data.get("evidenceTruncated"))
            existing_risk_score = previous_data.get("riskScore")
            candidate_risk_score = edge_data.get("riskScore")
            if candidate_risk_score is not None and (existing_risk_score is None or candidate_risk_score > existing_risk_score):
                previous_data["riskScore"] = candidate_risk_score
                previous_data["riskLevel"] = edge_data.get("riskLevel")
                previous_data["riskReason"] = edge_data.get("riskReason")
                previous_data["riskFactors"] = edge_data.get("riskFactors")
            continue
        edge_index_by_key[edge_key] = len(edges)
        edges.append(
            {
                "id": str(relation.id),
                "source": str(source_id),
                "target": str(target_id),
                "label": relation.relationship_type,
                "data": edge_data,
            }
        )
    return {
        "nodes": nodes,
        "edges": edges,
        "has_more": has_more_entities or has_more_relationships,
        "has_more_entities": has_more_entities,
        "has_more_relationships": has_more_relationships,
        "limit": limit,
        "offset": offset,
    }
