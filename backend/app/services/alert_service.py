"""Deterministic alert rules and user-scoped watchlist evaluation."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Alert, Entity, Investigation, Relationship, Risk, WatchlistEntry
from risk_engine import RelationshipRecord, dependency_orientation
from risk_engine.risk_engine import RiskResult


def create_monitoring_alert(
    db: Session,
    investigation: Investigation,
    change: Any,
    *,
    run_started_at: datetime,
) -> Alert | None:
    """Create one deduplicated alert for a material monitoring change."""
    alert_specs = {
        "RISK_INCREASED": ("RISK_INCREASE", "Risk increased during monitoring", "A persisted risk score increased by at least 10 points."),
        "NEW_HIGH_RISK_DEPENDENCY": ("HIGH_RISK_DEPENDENCY", "Dependency crossed into high risk", "A persisted risk score crossed the 75/100 high-risk threshold."),
        "NEW_CRITICAL_DEPENDENCY": ("NEW_CRITICAL_DEPENDENCY", "New critical dependency detected", "Monitoring detected a new critical dependency pattern."),
        "VERIFICATION_CONFLICT": ("VERIFICATION_CONFLICT", "Relationship verification conflict", "New persisted evidence changed a relationship to CONFLICTED."),
        "EVIDENCE_BECAME_STALE": ("STALE_EVIDENCE", "Supporting evidence became stale", "A verified relationship now relies on evidence older than the configured freshness window."),
        "NEW_UPSTREAM_DEPENDENCY": ("NEW_UPSTREAM_DEPENDENCY", "New upstream dependency discovered", "Monitoring detected a newly persisted upstream relationship."),
    }
    spec = alert_specs.get(change.change_type)
    if spec is None or investigation.demo_mode:
        return None
    alert_type, title, message = spec
    entity_id = _uuid_or_none(change.entity_id)
    relationship_id = _uuid_or_none(change.relationship_id)
    if db.scalar(select(Alert.id).where(
        Alert.investigation_id == investigation.id,
        Alert.dedupe_key == f"monitoring:{change.change_key[:120]}",
    )) is not None:
        return None
    same_run = select(Alert.id).where(
        Alert.investigation_id == investigation.id,
        Alert.alert_type == alert_type,
        Alert.created_at >= run_started_at,
    )
    if relationship_id is not None:
        same_run = same_run.where(Alert.relationship_id == relationship_id)
    elif entity_id is not None:
        same_run = same_run.where(Alert.entity_id == entity_id)
    if db.scalar(same_run) is not None:
        return None

    after = change.after_value or {}
    score = after.get("score") if isinstance(after, dict) else None
    alert = Alert(
        investigation_id=investigation.id,
        entity_id=entity_id,
        relationship_id=relationship_id,
        owner_id=investigation.owner_id,
        title=title,
        message=message,
        severity="high" if change.change_type in {"RISK_INCREASED", "NEW_HIGH_RISK_DEPENDENCY", "NEW_CRITICAL_DEPENDENCY", "VERIFICATION_CONFLICT"} else "medium",
        alert_type=alert_type,
        is_read=False,
        dedupe_key=f"monitoring:{change.change_key[:120]}",
        reason=_monitoring_alert_reason(change),
        risk_score=float(score) if isinstance(score, (int, float)) else None,
        evidence_ids=list(change.evidence_ids),
        risk_snapshot={"change_type": change.change_type, "change_key": change.change_key},
    )
    db.add(alert)
    db.flush()
    return alert


def _monitoring_alert_reason(change: Any) -> str:
    before = change.before_value or {}
    after = change.after_value or {}
    if change.change_type in {"RISK_INCREASED", "NEW_HIGH_RISK_DEPENDENCY"}:
        previous = before.get("score") if isinstance(before, dict) else None
        current = after.get("score") if isinstance(after, dict) else None
        if previous is not None and current is not None:
            return f"Persisted risk changed from {float(previous):g} to {float(current):g}/100."
        if current is not None:
            return f"Persisted risk reached {float(current):g}/100."
    return f"Persisted monitoring change: {change.change_type}."


def _uuid_or_none(value: object) -> UUID | None:
    if value is None:
        return None
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (ValueError, TypeError):
        return None


def evaluate_risk_alerts(
    db: Session,
    investigation: Investigation,
    result: RiskResult,
    *,
    snapshot_id: UUID,
    relationships: list[Relationship],
) -> list[Alert]:
    """Persist alerts only for observed calculated or verification state."""
    if investigation.demo_mode:
        return []

    created: list[Alert] = []
    previous = investigation.risk_analysis or {}
    current_entities_db = {
        str(item.id): item
        for item in db.scalars(select(Entity).where(Entity.investigation_id == investigation.id)).all()
    }
    previous_entities = {
        str(item.get("target_id")): item
        for item in previous.get("entity_risks", [])
        if isinstance(item, dict)
    }
    for assessment in result.entity_risks:
        earlier = previous_entities.get(assessment.target_id)
        previous_score = None if earlier is None else earlier.get("score")
        if assessment.score is not None and assessment.score >= 75 and (previous_score is None or float(previous_score) < 75):
            entity = current_entities_db.get(assessment.target_id)
            created.extend(_create(db, investigation, "HIGH_RISK_DEPENDENCY", assessment.level,
                "High risk dependency", f"{entity.name if entity else 'Entity'} has a calculated risk score of {assessment.score:g}/100.",
                entity_id=None if entity is None else entity.id, target_key=assessment.target_id,
                snapshot_id=snapshot_id, reason=assessment.reason, risk_score=assessment.score,
                owner_id=investigation.owner_id,
                state={"crossed_from": previous_score, "current": assessment.score},))
        if earlier and earlier.get("score") is not None and assessment.score is not None:
            increase = assessment.score - float(earlier["score"])
            if increase >= 10:
                entity = current_entities_db.get(assessment.target_id)
                created.extend(_create(db, investigation, "RISK_INCREASE", "high" if increase >= 20 else "medium",
                    "Risk increased", f"Calculated risk increased by {increase:g} points since the previous saved snapshot.",
                    entity_id=None if entity is None else entity.id, target_key=assessment.target_id,
                    snapshot_id=snapshot_id, reason=f"Previous: {float(earlier['score']):g}; current: {assessment.score:g}.",
                    risk_score=assessment.score, owner_id=investigation.owner_id,
                    state={"previous": earlier.get("score"), "current": assessment.score},))

    previous_critical = {
        (str(item.get("type")), str(item.get("entity_id")), tuple(sorted(item.get("related_entity_ids", []))))
        for item in previous.get("critical_dependencies", []) if isinstance(item, dict)
    }
    for dependency in result.critical_dependencies:
        pattern_type = str(dependency.get("type", ""))
        entity_id_text = str(dependency.get("entity_id", ""))
        related = tuple(sorted(str(value) for value in dependency.get("related_entity_ids", [])))
        if pattern_type == "SINGLE_SOURCE":
            entity = _entity(db, entity_id_text)
            created.extend(_create(db, investigation, "SINGLE_SOURCE_DEPENDENCY", str(dependency.get("severity", "medium")),
                "Single-source dependency detected", str(dependency["explanation"]),
                entity_id=None if entity is None else entity.id, target_key=entity_id_text,
                snapshot_id=snapshot_id, reason=str(dependency["explanation"]), owner_id=investigation.owner_id,
                state={"related": related},))
        elif pattern_type == "GEOGRAPHIC_CONCENTRATION":
            entity = current_entities_db.get(entity_id_text)
            created.extend(_create(db, investigation, "GEOGRAPHIC_CONCENTRATION", str(dependency.get("severity", "medium")),
                "Geographic concentration detected", str(dependency["explanation"]),
                entity_id=None if entity is None else entity.id, target_key=entity_id_text,
                snapshot_id=snapshot_id, reason=str(dependency["explanation"]), owner_id=investigation.owner_id,
                state={"related": related},))
        elif pattern_type == "HIGH_CONCENTRATION":
            entity = current_entities_db.get(entity_id_text)
            created.extend(_create(db, investigation, "HIGH_CONCENTRATION", str(dependency.get("severity", "medium")),
                "Supplier concentration detected", str(dependency["explanation"]),
                entity_id=None if entity is None else entity.id, target_key=entity_id_text,
                snapshot_id=snapshot_id, reason=str(dependency["explanation"]), owner_id=investigation.owner_id,
                state={"related": related},))
        elif pattern_type == "COMMON_DEPENDENCY":
            entity = current_entities_db.get(entity_id_text)
            created.extend(_create(db, investigation, "COMMON_DEPENDENCY", str(dependency.get("severity", "medium")),
                "Shared verified dependency detected", str(dependency["explanation"]),
                entity_id=None if entity is None else entity.id, target_key=entity_id_text,
                snapshot_id=snapshot_id, reason=str(dependency["explanation"]), owner_id=investigation.owner_id,
                state={"related_consumers": related},))
        if (pattern_type, entity_id_text, related) not in previous_critical and previous.get("snapshot_id"):
            entity = current_entities_db.get(entity_id_text)
            created.extend(_create(db, investigation, "NEW_CRITICAL_DEPENDENCY", str(dependency.get("severity", "medium")),
                "New critical dependency pattern", str(dependency["explanation"]),
                entity_id=None if entity is None else entity.id, target_key=entity_id_text,
                snapshot_id=snapshot_id, reason=str(dependency["explanation"]), owner_id=investigation.owner_id,
                state={"type": pattern_type, "related": related},))

    relation_by_id = {str(item.id): item for item in relationships}
    for assessment in result.relationship_risks:
        freshness = next((factor for factor in assessment.factors if factor.key == "evidence_freshness"), None)
        if freshness and freshness.score is not None and freshness.score >= 75:
            relation = relation_by_id.get(assessment.target_id)
            created.extend(_create(db, investigation, "STALE_EVIDENCE", "medium", "Dependency evidence is stale",
                freshness.explanation, entity_id=None if relation is None else relation.source_entity_id,
                relationship_id=None if relation is None else relation.id, target_key=assessment.target_id,
                snapshot_id=snapshot_id, reason=freshness.explanation,
                evidence_ids=list(freshness.evidence_ids), owner_id=investigation.owner_id,
                state={"stale_score": freshness.score},))
    previous_relationships = {
        str(item.get("target_id")) for item in previous.get("relationship_risks", []) if isinstance(item, dict)
    }
    for assessment in result.relationship_risks:
        if not previous.get("snapshot_id") or assessment.target_id in previous_relationships:
            continue
        relation = relation_by_id.get(assessment.target_id)
        if relation is None:
            continue
        direction = dependency_orientation(RelationshipRecord(
            id=str(relation.id), source_id=str(relation.source_entity_id), target_id=str(relation.target_entity_id),
            relationship_type=relation.relationship_type, verification_status=relation.verification_status,
            confidence=relation.confidence, metadata=relation.metadata_json or {},
        ))
        if direction is None:
            continue
        entity = current_entities_db.get(str(relation.source_entity_id))
        created.extend(_create(db, investigation, "NEW_UPSTREAM_DEPENDENCY", "medium",
            "New verified upstream relationship", f"A new verified {relation.relationship_type} relationship entered the calculated dependency graph.",
            entity_id=None if entity is None else entity.id, relationship_id=relation.id,
            target_key=assessment.target_id, snapshot_id=snapshot_id,
            reason="The relationship is present in the current verified graph and absent from the prior risk snapshot.",
            owner_id=investigation.owner_id, state={"relationship_id": assessment.target_id},))

    for relation in relationships:
        status = relation.verification_status.upper()
        if status != "CONFLICTED" or investigation.demo_mode:
            continue
        verification = (relation.metadata_json or {}).get("verification", {})
        evidence_ids = verification.get("conflicting_evidence_ids", []) if isinstance(verification, dict) else []
        created.extend(_create(db, investigation, "VERIFICATION_CONFLICT", "high",
            "Conflicting relationship evidence", f"Verification marked {relation.relationship_type} as CONFLICTED; the conflict is preserved for review.",
            entity_id=relation.source_entity_id, relationship_id=relation.id,
            target_key=str(relation.id), snapshot_id=snapshot_id,
            reason="Conflicting evidence prevents treating this relationship as verified.",
            evidence_ids=[str(item) for item in evidence_ids], owner_id=investigation.owner_id,
            state={"verification_status": status},))

    created.extend(_evaluate_watchlist(db, investigation, result, snapshot_id))
    db.flush()
    return created


def _evaluate_watchlist(
    db: Session,
    investigation: Investigation,
    result: RiskResult,
    snapshot_id: UUID,
) -> list[Alert]:
    entries = db.scalars(
        select(WatchlistEntry).where(WatchlistEntry.owner_id.is_not(None))
    ).all()
    entity_scores = {item.target_id: item for item in result.entity_risks}
    relation_scores = {item.target_id: item for item in result.relationship_risks}
    created: list[Alert] = []
    for entry in entries:
        if entry.investigation_id is not None and entry.investigation_id != investigation.id:
            continue
        resource_type = entry.target_type or "entity"
        resource_id = str(entry.target_id or entry.entity_id or entry.relationship_id or entry.investigation_id or "")
        if not resource_id:
            continue
        if resource_type == "entity":
            assessment = entity_scores.get(resource_id)
        elif resource_type == "relationship":
            assessment = relation_scores.get(resource_id)
        elif resource_type in {"investigation", "risk_condition"}:
            assessment = None
        else:
            continue
        score = result.summary.get("overall_score") if assessment is None else assessment.score
        level = result.summary.get("overall_level", "UNKNOWN") if assessment is None else assessment.level
        threshold = entry.risk_threshold
        condition = entry.condition_json or {}
        if threshold is None:
            raw_threshold = condition.get("risk_threshold")
            threshold = float(raw_threshold) if isinstance(raw_threshold, (int, float)) else None
        if threshold is None or score is None or float(score) < threshold:
            entry.last_observed = {"score": score, "level": level, "snapshot_id": str(snapshot_id)}
            continue
        previous = entry.last_observed or {}
        if previous.get("snapshot_id") == str(snapshot_id):
            continue
        if previous.get("score") is not None and float(previous["score"]) >= threshold:
            # A still-breached condition is not a new state change.
            entry.last_observed = {"score": score, "level": level, "snapshot_id": str(snapshot_id)}
            continue
        entity_id = entry.entity_id
        relationship_id = entry.relationship_id
        created.extend(_create(db, investigation, "WATCHLIST_CHANGE", "high" if float(score) >= 75 else "medium",
            "Watched risk condition crossed its threshold",
            f"Watched {resource_type} risk crossed the configured threshold of {threshold:g}/100 (current: {float(score):g}/100).",
            entity_id=entity_id, relationship_id=relationship_id, target_key=f"{resource_type}:{resource_id}",
            snapshot_id=snapshot_id, reason=f"Watchlist threshold crossing: {threshold:g}/100 → {float(score):g}/100.",
            risk_score=float(score), owner_id=entry.owner_id,
            state={"threshold": threshold, "score": score},))
        entry.last_observed = {"score": score, "level": level, "snapshot_id": str(snapshot_id)}
    return created


def _entity(db: Session, entity_id: str) -> Entity | None:
    try:
        return db.get(Entity, UUID(entity_id))
    except ValueError:
        return None


def _create(
    db: Session,
    investigation: Investigation,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    *,
    target_key: str,
    snapshot_id: UUID,
    reason: str,
    entity_id: UUID | None = None,
    relationship_id: UUID | None = None,
    evidence_ids: list[str] | None = None,
    risk_score: float | None = None,
    owner_id: UUID | None = None,
    state: dict[str, Any] | None = None,
) -> list[Alert]:
    dedupe_material = {
        "investigation_id": str(investigation.id),
        "alert_type": alert_type,
        "target": target_key,
        "owner": str(owner_id) if owner_id else None,
        "state": state or {},
    }
    digest = hashlib.sha256(json.dumps(dedupe_material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    dedupe_key = f"{alert_type.lower()}:{digest}"
    exists = db.scalar(select(Alert.id).where(
        Alert.investigation_id == investigation.id,
        Alert.dedupe_key == dedupe_key,
    ))
    if exists is not None:
        return []
    alert = Alert(
        investigation_id=investigation.id,
        entity_id=entity_id,
        relationship_id=relationship_id,
        owner_id=owner_id,
        alert_type=alert_type,
        title=title,
        message=message,
        severity=severity.lower(),
        reason=reason,
        risk_score=risk_score,
        evidence_ids=sorted(set(evidence_ids or [])),
        risk_snapshot={"snapshot_id": str(snapshot_id), "state": state or {}},
        dedupe_key=dedupe_key,
    )
    try:
        with db.begin_nested():
            db.add(alert)
            db.flush()
    except IntegrityError:
        return []
    return [alert]
