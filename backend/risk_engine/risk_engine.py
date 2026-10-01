"""Pure risk calculation over a bounded, verified dependency graph."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import re
from typing import Any, Mapping, Sequence

from .critical_dependency import detect_critical_dependencies
from .geographic_risk import geographic_concentration
from .risk_propagation import propagate_risk
from .risk_scoring import RiskAssessment, RiskFactor, make_factor, risk_level, weighted_score
from .single_point_failure import single_source
from .concentration import structural_concentration


@dataclass(frozen=True)
class RiskConfig:
    max_depth: int = 6
    propagation_decay: float = 0.72
    stale_after_days: int = 365
    deep_dependency_edges: int = 4
    geographic_share_threshold: float = 0.67
    max_entities: int = 5000
    thresholds: tuple[float, float, float] = (25.0, 50.0, 75.0)
    entity_weights: Mapping[str, float] = field(default_factory=lambda: {
        "dependency_depth": 0.20,
        "supplier_concentration": 0.20,
        "centrality": 0.15,
        "geographic_concentration": 0.15,
        "criticality": 0.10,
        "verification_confidence": 0.10,
        "evidence_freshness": 0.10,
    })
    relationship_weights: Mapping[str, float] = field(default_factory=lambda: {
        "dependency_depth": 0.15,
        "supplier_concentration": 0.15,
        "centrality": 0.10,
        "geographic_concentration": 0.10,
        "criticality": 0.15,
        "verification_confidence": 0.15,
        "evidence_freshness": 0.10,
        "upstream_exposure": 0.10,
    })


DEFAULT_CONFIG = RiskConfig()


@dataclass(frozen=True)
class EntityRecord:
    id: str
    name: str
    entity_type: str
    jurisdiction: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelationshipRecord:
    id: str
    source_id: str
    target_id: str
    relationship_type: str
    verification_status: str
    confidence: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    relationship_id: str
    source: str
    source_type: str
    published_date: date | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskResult:
    entity_risks: tuple[RiskAssessment, ...]
    relationship_risks: tuple[RiskAssessment, ...]
    critical_dependencies: tuple[Mapping[str, Any], ...]
    summary: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity_risks": [risk.as_dict() for risk in self.entity_risks],
            "relationship_risks": [risk.as_dict() for risk in self.relationship_risks],
            "critical_dependencies": [dict(item) for item in self.critical_dependencies],
            "summary": dict(self.summary),
        }


FORWARD_DEPENDENCY_TYPES = {
    "DEPENDS_ON", "SOURCES_FROM", "PURCHASES_FROM", "BUYS_FROM", "USES",
    "USES_MATERIAL", "CONTRACTS_WITH", "SUBCONTRACTS_TO", "PROCESSES",
    "PROCESSES_MATERIAL", "REQUIRES",
}
REVERSE_DEPENDENCY_TYPES = {
    "SUPPLIES", "PROVIDES", "PRODUCES_FOR", "MANUFACTURES_FOR", "SELLS_TO",
}


def calculate_risk(
    entities: Sequence[EntityRecord],
    relationships: Sequence[RelationshipRecord],
    evidence: Sequence[EvidenceRecord],
    *,
    target_name: str | None = None,
    as_of: datetime | None = None,
    config: RiskConfig = DEFAULT_CONFIG,
) -> RiskResult:
    """Calculate scores without mutating input records or filling unknown data."""
    if len(entities) > config.max_entities:
        raise ValueError(f"Risk analysis is limited to {config.max_entities} entities per investigation.")

    as_of = _as_utc(as_of or datetime.now(timezone.utc))
    entity_by_id = {str(entity.id): entity for entity in entities}
    entity_payload = {
        entity_id: {
            "name": entity.name,
            "entity_type": entity.entity_type,
            "jurisdiction": entity.jurisdiction,
            "metadata": dict(entity.metadata or {}),
        }
        for entity_id, entity in entity_by_id.items()
    }
    evidence_by_relationship: dict[str, list[EvidenceRecord]] = defaultdict(list)
    for row in evidence:
        if not _is_demo_evidence(row):
            evidence_by_relationship[str(row.relationship_id)].append(row)

    dependency_edges: list[dict[str, Any]] = []
    riskable_relationships: list[RelationshipRecord] = []
    for relation in sorted(relationships, key=lambda item: str(item.id)):
        if str(relation.verification_status).upper() != "VERIFIED":
            continue
        if _is_demo_relationship(relation):
            continue
        riskable_relationships.append(relation)
        oriented = _dependency_orientation(relation)
        if oriented is not None:
            source_id, target_id = oriented
        else:
            continue
        if source_id in entity_by_id and target_id in entity_by_id:
            dependency_edges.append({
                "source_id": source_id,
                "target_id": target_id,
                "relationship_id": str(relation.id),
                "metadata": dict(relation.metadata or {}),
                "confidence": _confidence(relation.confidence),
            })

    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in dependency_edges:
        outgoing[edge["source_id"]].append(edge)
        incoming[edge["target_id"]].append(edge)
        adjacency[edge["source_id"]].append(edge["target_id"])
    for node_edges in outgoing.values():
        node_edges.sort(key=lambda edge: (edge["target_id"], edge["relationship_id"]))

    target_id = _resolve_target(target_name, entities)
    depths = _reachable_depths(target_id, adjacency, config.max_depth)
    degree = {entity_id: len(outgoing.get(entity_id, [])) + len(incoming.get(entity_id, [])) for entity_id in entity_by_id}
    max_degree = max(degree.values(), default=0)

    entity_factors: dict[str, tuple[RiskFactor, ...]] = {}
    local_scores: dict[str, float | None] = {}
    for entity_id in sorted(entity_by_id):
        entity = entity_by_id[entity_id]
        related_edges = outgoing.get(entity_id, []) + incoming.get(entity_id, [])
        freshness = _freshness(related_edges, evidence_by_relationship, as_of, config.stale_after_days)
        factor_list = [
            make_factor(
                "dependency_depth", "Dependency depth",
                None if entity_id not in depths else min(100.0, 100.0 * depths[entity_id] / config.max_depth),
                "The investigation target was not uniquely resolved in this graph." if entity_id not in depths else f"Entity is {depths[entity_id]} verified dependency hop(s) from the investigation target.",
                source="verified graph and investigation plan",
            ),
        ]
        count = len(outgoing.get(entity_id, []))
        concentration, concentration_reason = structural_concentration(count)
        factor_list.append(make_factor("supplier_concentration", "Verified dependency count", concentration, concentration_reason, source="verified graph"))
        factor_list.append(make_factor(
            "centrality", "Dependency centrality",
            None if max_degree == 0 else 100.0 * degree[entity_id] / max_degree,
            "No verified graph edges are available." if max_degree == 0 else f"Entity has {degree[entity_id]} verified incident relationship(s); normalized against the most connected entity in this investigation.",
            source="verified graph",
        ))
        geo_score, geo_reason = geographic_concentration(
            entity_by_id[edge["target_id"]].jurisdiction for edge in outgoing.get(entity_id, [])
        )
        factor_list.append(make_factor("geographic_concentration", "Geographic concentration", geo_score, geo_reason, source="entity jurisdiction metadata"))
        criticality, criticality_reason, criticality_source = _criticality(entity.metadata)
        factor_list.append(make_factor("criticality", "Recorded criticality", criticality, criticality_reason, source=criticality_source))
        confidences = [edge["confidence"] for edge in related_edges if edge["confidence"] is not None]
        factor_list.append(make_factor(
            "verification_confidence", "Verification uncertainty",
            None if not confidences else 100.0 * (1.0 - sum(confidences) / len(confidences)),
            "No confidence value is stored for verified relationships connected to this entity." if not confidences else f"Mean stored verification confidence is {sum(confidences) / len(confidences) * 100:.1f}%; lower confidence increases uncertainty risk.",
            source="relationship verification confidence",
        ))
        factor_list.append(make_factor(
            "evidence_freshness", "Evidence age", freshness[0], freshness[1],
            source="published dates on non-demo evidence", evidence_ids=freshness[2],
        ))
        entity_factors[entity_id] = tuple(factor_list)
        local_scores[entity_id] = weighted_score(factor_list, dict(config.entity_weights))

    propagation_edges = [
        (edge["source_id"], edge["target_id"], edge["confidence"])
        for edge in dependency_edges
    ]
    propagated_totals = propagate_risk(
        local_scores, propagation_edges, max_depth=config.max_depth, decay=config.propagation_decay,
    )
    entity_risks: list[RiskAssessment] = []
    for entity_id in sorted(entity_by_id):
        local = local_scores[entity_id]
        total = propagated_totals.get(entity_id)
        propagated_component = None if total is None else round(max(0.0, total - (local or 0.0)), 2)
        final_score = None if local is None and total is None else round(max(local or 0.0, total or 0.0), 2)
        factors = list(entity_factors[entity_id])
        if propagation_edges:
            factors.append(make_factor(
                "upstream_exposure", "Propagated upstream exposure", propagated_component,
                "No downstream risk score is available to propagate." if total is None else f"Downstream exposure adds {propagated_component:g} points after confidence weighting and {config.propagation_decay:g} per-hop decay.",
                source="verified graph propagation",
            ))
        entity = entity_by_id[entity_id]
        entity_risks.append(RiskAssessment(
            "entity", entity_id, final_score, risk_level(final_score, config.thresholds), tuple(factors),
            propagated_component,
            _explanation(factors, local, final_score, propagated_component),
        ))

    relationship_risks: list[RiskAssessment] = []
    edge_by_relation = {str(edge["relationship_id"]): edge for edge in dependency_edges}
    for relation in riskable_relationships:
        relation_id = str(relation.id)
        edge = edge_by_relation.get(relation_id)
        if edge is None:
            orientation = _dependency_orientation(relation)
            source_id, target_id_for_edge = orientation or ("", "")
            edge = {"source_id": source_id, "target_id": target_id_for_edge, "relationship_id": relation_id, "confidence": _confidence(relation.confidence), "metadata": dict(relation.metadata or {})}
        source_id, target_id_for_edge = edge["source_id"], edge["target_id"]
        related = outgoing.get(source_id, [])
        freshness = _freshness([edge], evidence_by_relationship, as_of, config.stale_after_days)
        count = len(related)
        concentration, concentration_reason = structural_concentration(count) if edge["source_id"] else (None, "Relationship type does not establish dependency direction.")
        geography, geography_reason = geographic_concentration(
            entity_by_id[item["target_id"]].jurisdiction for item in related if item["target_id"] in entity_by_id
        )
        depth = depths.get(source_id)
        target_entity = entity_by_id.get(target_id_for_edge)
        source_entity = entity_by_id.get(source_id)
        confidence = edge["confidence"]
        downstream = propagated_totals.get(target_id_for_edge)
        confidence_risk = None if confidence is None else 100.0 * (1.0 - confidence)
        factor_list = (
            make_factor("dependency_depth", "Dependency depth", None if depth is None or not edge["source_id"] else min(100.0, 100.0 * (depth + 1) / config.max_depth), "Relationship type does not establish dependency direction." if not edge["source_id"] else ("The dependency endpoint is not reachable from the uniquely resolved investigation target." if depth is None else f"This relationship extends the verified chain by one hop from depth {depth}."), source="verified graph and investigation plan"),
            make_factor("supplier_concentration", "Verified dependency count", concentration, concentration_reason, source="verified graph"),
            make_factor("centrality", "Dependency centrality", None if max_degree == 0 or not source_id else 100.0 * degree.get(source_id, 0) / max_degree, "No verified graph edges or known relationship direction are available." if max_degree == 0 or not source_id else f"The dependency source has {degree.get(source_id, 0)} verified incident relationship(s).", source="verified graph"),
            make_factor("geographic_concentration", "Geographic concentration", geography, geography_reason, source="entity jurisdiction metadata"),
            make_factor("criticality", "Recorded provider criticality", None if target_entity is None else _criticality(target_entity.metadata)[0], "Provider entity is not present in this investigation." if target_entity is None else _criticality(target_entity.metadata)[1], source=None if target_entity is None else _criticality(target_entity.metadata)[2]),
            make_factor("verification_confidence", "Verification uncertainty", confidence_risk, "No relationship confidence is stored." if confidence is None else f"Stored verification confidence is {confidence * 100:.1f}%; lower confidence increases uncertainty risk.", source="relationship verification confidence"),
            make_factor("evidence_freshness", "Evidence age", freshness[0], freshness[1], source="published dates on non-demo evidence", evidence_ids=freshness[2]),
            make_factor("upstream_exposure", "Propagated provider exposure", downstream, "The provider has no calculated risk score." if downstream is None else f"Provider downstream exposure is {downstream:g}/100 before relationship-hop decay.", source="verified graph propagation"),
        )
        score = weighted_score(factor_list, dict(config.relationship_weights))
        relation_source = source_entity.name if source_entity is not None else "dependency source"
        relation_target = target_entity.name if target_entity is not None else "provider"
        reason = f"{relation_source} → {relation_target} risk uses the relationship's own confidence, graph position, provider criticality, and evidence freshness factors."
        relationship_risks.append(RiskAssessment("relationship", relation_id, score, risk_level(score, config.thresholds), factor_list, None, reason))

    critical_dependencies = detect_critical_dependencies(
        entity_payload, dependency_edges,
        minimum_deep_edges=config.deep_dependency_edges,
        geographic_share_threshold=config.geographic_share_threshold,
        maximum_depth=config.max_depth,
    )
    known_scores = [risk.score for risk in entity_risks if risk.score is not None]
    unknown_entities = sum(risk.score is None for risk in entity_risks)
    verified_count = len(riskable_relationships)
    summary = {
        "overall_score": None if not known_scores else round(sum(known_scores) / len(known_scores), 2),
        "overall_level": risk_level(None if not known_scores else sum(known_scores) / len(known_scores), config.thresholds),
        "risk_model": "hdi-risk-v1",
        "score_scale": "0-100",
        "configuration": {
            "max_depth": config.max_depth,
            "propagation_decay": config.propagation_decay,
            "stale_after_days": config.stale_after_days,
            "thresholds": {"medium": config.thresholds[0], "high": config.thresholds[1], "critical": config.thresholds[2]},
            "entity_weights": dict(config.entity_weights),
            "relationship_weights": dict(config.relationship_weights),
        },
        "target_entity_id": target_id,
        "entities_scored": len(known_scores),
        "entities_unknown": unknown_entities,
        "verified_relationships_scored": verified_count,
        "relationship_status_counts": _relationship_status_counts(relationships),
        "unknown_factor_count": sum(f.status == "UNKNOWN" for risk in [*entity_risks, *relationship_risks] for f in risk.factors),
        "critical_dependencies": list(critical_dependencies),
        "propagation": {"max_depth": config.max_depth, "decay_per_hop": config.propagation_decay, "direction": "provider-to-dependent"},
    }
    return RiskResult(tuple(entity_risks), tuple(relationship_risks), tuple(critical_dependencies), summary)


def _relationship_status_counts(relationships: Sequence[RelationshipRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relationship in relationships:
        status = str(relationship.verification_status or "UNKNOWN").upper()
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _dependency_orientation(relation: RelationshipRecord) -> tuple[str, str] | None:
    normalized = re.sub(r"[^A-Z0-9]+", "_", relation.relationship_type.upper()).strip("_")
    if normalized in REVERSE_DEPENDENCY_TYPES:
        return str(relation.target_id), str(relation.source_id)
    if normalized in FORWARD_DEPENDENCY_TYPES:
        return str(relation.source_id), str(relation.target_id)
    return None


def dependency_orientation(relation: RelationshipRecord) -> tuple[str, str] | None:
    """Return consumer/provider IDs only for relationship types with known direction."""
    return _dependency_orientation(relation)


def _confidence(value: float | None) -> float | None:
    if value is None:
        return None
    normalized = float(value)
    if normalized > 1:
        normalized /= 100.0
    return min(1.0, max(0.0, normalized))


def _is_demo_relationship(relation: RelationshipRecord) -> bool:
    if "DEMO" in str(relation.verification_status).upper():
        return True
    metadata = relation.metadata or {}
    return bool(metadata.get("demo_only") or metadata.get("demo_mode"))


def _is_demo_evidence(evidence: EvidenceRecord) -> bool:
    return (
        bool((evidence.metadata or {}).get("demo_only"))
        or "DEMO" in evidence.source.upper()
        or "DEMO" in evidence.source_type.upper()
    )


def _criticality(metadata: Mapping[str, Any]) -> tuple[float | None, str, str | None]:
    candidates: list[tuple[str, Any]] = []
    candidates.extend((key, metadata.get(key)) for key in ("criticality_score", "material_criticality", "criticality", "criticality_level"))
    nested = metadata.get("risk")
    if isinstance(nested, Mapping):
        candidates.extend((f"risk.{key}", nested.get(key)) for key in ("criticality_score", "criticality", "criticality_level"))
    for key, value in candidates:
        provenance_owner = metadata
        if key.startswith("risk.") and isinstance(nested, Mapping):
            provenance_owner = nested
        provenance = (
            provenance_owner.get(f"{key.split('.')[-1]}_source")
            or provenance_owner.get("source")
            or provenance_owner.get("source_url")
            or provenance_owner.get("source_evidence_ids")
            or provenance_owner.get("evidence_ids")
        )
        if not provenance:
            continue
        if isinstance(value, bool):
            return (100.0 if value else 0.0), f"Source metadata records {'critical' if value else 'non-critical'} status in '{key}'.", f"entity metadata: {key}"
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = None
        if score is not None:
            if score > 1.0:
                score = score / 100.0
            return min(100.0, max(0.0, score * 100.0)), f"Source metadata records a criticality value in '{key}'.", f"entity metadata: {key}"
        if isinstance(value, str):
            label = value.strip().casefold()
            mapped = {"low": 25.0, "medium": 50.0, "moderate": 50.0, "high": 75.0, "critical": 100.0}.get(label)
            if mapped is not None:
                return mapped, f"Source metadata reports '{value}' criticality in '{key}'.", f"entity metadata: {key}"
    return None, "No source-backed criticality value is recorded.", None


def _freshness(
    edges: Sequence[Mapping[str, Any]],
    evidence_by_relationship: Mapping[str, list[EvidenceRecord]],
    as_of: datetime,
    stale_after_days: int,
) -> tuple[float | None, str, tuple[str, ...]]:
    evidence_rows: list[EvidenceRecord] = []
    for edge in edges:
        evidence_rows.extend(evidence_by_relationship.get(str(edge["relationship_id"]), []))
    published = [(row, row.published_date) for row in evidence_rows if row.published_date is not None]
    if not published:
        return None, "No publication dates are recorded on non-demo supporting evidence.", ()
    oldest = min(value for _, value in published)
    age_days = max(0, (as_of.date() - oldest).days)
    score = min(100.0, 100.0 * age_days / max(1, stale_after_days))
    evidence_ids = tuple(sorted(str(row.id) for row, _ in published))
    return score, f"Oldest relevant published evidence is {age_days} day(s) old; staleness threshold is {stale_after_days} days.", evidence_ids


def _resolve_target(target_name: str | None, entities: Sequence[EntityRecord]) -> str | None:
    if not target_name:
        return None
    normalize = lambda value: re.sub(r"[^a-z0-9]+", "", value.casefold())
    target = normalize(target_name)
    exact = [entity for entity in entities if normalize(entity.name) == target]
    if len(exact) == 1:
        return str(exact[0].id)
    partial = [entity for entity in entities if target and (target in normalize(entity.name) or normalize(entity.name) in target)]
    return str(partial[0].id) if len(partial) == 1 else None


def _reachable_depths(target_id: str | None, adjacency: Mapping[str, list[str]], maximum_depth: int) -> dict[str, int]:
    if target_id is None:
        return {}
    depths = {target_id: 0}
    queue = deque([target_id])
    while queue:
        source = queue.popleft()
        depth = depths[source]
        if depth >= maximum_depth:
            continue
        for target in sorted(adjacency.get(source, [])):
            if target not in depths:
                depths[target] = depth + 1
                queue.append(target)
    return depths


def _explanation(
    factors: Sequence[RiskFactor],
    local_score: float | None,
    final_score: float | None,
    propagated_component: float | None,
) -> str:
    if final_score is None:
        return "Risk is UNKNOWN because no verified relationship or source-backed risk factor is available."
    material = sorted(
        (factor for factor in factors if factor.status == "KNOWN" and factor.score is not None),
        key=lambda factor: (-float(factor.score), factor.key),
    )[:3]
    reason = "; ".join(f"{factor.label.lower()}={factor.score:g}" for factor in material)
    if propagated_component is not None and propagated_component > 0:
        reason += f"; downstream propagation adds up to {propagated_component:g} points"
    return f"Score {final_score:g}/100 uses the weighted mean of available data-backed factors" + (f" ({reason})." if reason else ".")


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
