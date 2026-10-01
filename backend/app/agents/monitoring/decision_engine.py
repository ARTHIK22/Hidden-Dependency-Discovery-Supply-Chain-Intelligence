from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DetectedChange:
    change_type: str
    change_key: str
    entity_id: str | None = None
    relationship_id: str | None = None
    before_value: dict[str, Any] | None = None
    after_value: dict[str, Any] | None = None
    evidence_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_ids"] = list(self.evidence_ids)
        return value


def detect_changes(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[DetectedChange]:
    """Compare compact persisted-state fingerprints; never invent observations."""
    if previous is None:
        return []
    changes: list[DetectedChange] = []
    before_entities = previous.get("entities", {})
    after_entities = current.get("entities", {})
    before_relationships = previous.get("relationships", {})
    after_relationships = current.get("relationships", {})
    before_evidence = previous.get("evidence", {})
    after_evidence = current.get("evidence", {})

    if previous.get("investigation_state", {}) != current.get("investigation_state", {}):
        changes.append(DetectedChange(
            "INVESTIGATION_CONFIG_CHANGED", "investigation-config",
            before_value=previous.get("investigation_state", {}),
            after_value=current.get("investigation_state", {}),
        ))

    for entity_id in sorted(after_entities.keys() - before_entities.keys()):
        changes.append(DetectedChange("NEW_ENTITY", f"entity:{entity_id}", entity_id=entity_id, after_value=after_entities[entity_id]))
    for entity_id in sorted(before_entities.keys() - after_entities.keys()):
        changes.append(DetectedChange("ENTITY_REMOVED", f"entity:{entity_id}", entity_id=entity_id, before_value=before_entities[entity_id]))
    for entity_id in sorted(before_entities.keys() & after_entities.keys()):
        before, after = before_entities[entity_id], after_entities[entity_id]
        if before != after:
            changes.append(DetectedChange(
                "ENTITY_CHANGED", f"entity-changed:{entity_id}", entity_id=entity_id,
                before_value=before, after_value=after,
            ))

    for relationship_id in sorted(after_relationships.keys() - before_relationships.keys()):
        relation = after_relationships[relationship_id]
        evidence_ids = tuple(sorted(relation.get("evidence_ids", [])))
        changes.append(DetectedChange(
            "NEW_RELATIONSHIP", f"relationship:{relationship_id}",
            entity_id=relation.get("consumer_id"), relationship_id=relationship_id,
            after_value=relation, evidence_ids=evidence_ids,
        ))
        provider_id = relation.get("provider_id")
        if provider_id:
            changes.append(DetectedChange(
                "NEW_UPSTREAM_DEPENDENCY", f"upstream:{relationship_id}:{provider_id}",
                entity_id=provider_id, relationship_id=relationship_id,
                after_value={"provider_id": provider_id, "consumer_id": relation.get("consumer_id")},
                evidence_ids=evidence_ids,
            ))
    for relationship_id in sorted(before_relationships.keys() - after_relationships.keys()):
        relation = before_relationships[relationship_id]
        changes.append(DetectedChange(
            "RELATIONSHIP_REMOVED", f"relationship:{relationship_id}",
            entity_id=relation.get("consumer_id"), relationship_id=relationship_id,
            before_value=relation,
            evidence_ids=tuple(sorted(relation.get("evidence_ids", []))),
        ))
    for relationship_id in sorted(before_relationships.keys() & after_relationships.keys()):
        before, after = before_relationships[relationship_id], after_relationships[relationship_id]
        if before == after:
            continue
        evidence_ids = tuple(sorted(set(before.get("evidence_ids", [])) | set(after.get("evidence_ids", []))))
        changes.append(DetectedChange(
            "RELATIONSHIP_CHANGED", f"relationship:{relationship_id}",
            entity_id=after.get("consumer_id"), relationship_id=relationship_id,
            before_value=before, after_value=after, evidence_ids=evidence_ids,
        ))
        status = str(after.get("verification_status", "")).upper()
        if status == "CONFLICTED" and str(before.get("verification_status", "")).upper() != "CONFLICTED":
            changes.append(DetectedChange(
                "VERIFICATION_CONFLICT", f"conflict:{relationship_id}:{after_relationships[relationship_id].get('verification_status')}",
                entity_id=after.get("consumer_id"), relationship_id=relationship_id,
                before_value={"verification_status": before.get("verification_status")},
                after_value={"verification_status": after.get("verification_status")}, evidence_ids=evidence_ids,
            ))
        if set(before.get("evidence_ids", [])) != set(after.get("evidence_ids", [])):
            changes.append(DetectedChange(
                "EVIDENCE_CHANGED", f"relationship-evidence:{relationship_id}",
                entity_id=after.get("consumer_id"), relationship_id=relationship_id,
                before_value={"evidence_ids": sorted(before.get("evidence_ids", []))},
                after_value={"evidence_ids": sorted(after.get("evidence_ids", []))}, evidence_ids=evidence_ids,
            ))

    evidence_ids_all = before_evidence.keys() | after_evidence.keys()
    changed_evidence_by_relationship: dict[str, set[str]] = {}
    for evidence_id in sorted(evidence_ids_all):
        before, after = before_evidence.get(evidence_id), after_evidence.get(evidence_id)
        if before == after:
            continue
        relation_id = (after or before or {}).get("relationship_id")
        changed_evidence_by_relationship.setdefault(str(relation_id or "unlinked"), set()).add(evidence_id)
    for relation_id, values in sorted(changed_evidence_by_relationship.items()):
        changes.append(DetectedChange(
            "EVIDENCE_CHANGED", f"evidence:{relation_id}:{','.join(sorted(values))}",
            relationship_id=None if relation_id == "unlinked" else relation_id,
            evidence_ids=tuple(sorted(values)),
            before_value={"changed_evidence_ids": sorted(value for value in values if value in before_evidence)},
            after_value={"changed_evidence_ids": sorted(value for value in values if value in after_evidence)},
        ))

    before_stale = set(previous.get("stale_evidence_ids", []))
    after_stale = set(current.get("stale_evidence_ids", []))
    for evidence_id in sorted(after_stale - before_stale):
        evidence = after_evidence.get(evidence_id, {})
        changes.append(DetectedChange(
            "EVIDENCE_BECAME_STALE", f"stale-evidence:{evidence_id}",
            relationship_id=evidence.get("relationship_id"), evidence_ids=(evidence_id,),
            before_value={"stale": False}, after_value={"stale": True},
        ))

    previous_risks = previous.get("risk_scores", {})
    current_risks = current.get("risk_scores", {})
    for target_id in sorted(current_risks.keys() - previous_risks.keys()):
        score = current_risks[target_id]
        if score is None:
            continue
        relationship_id = target_id if target_id in after_relationships else None
        changes.append(DetectedChange(
            "RISK_ASSESSMENT_ADDED", f"risk-added:{target_id}:{float(score):g}",
            entity_id=None if relationship_id else target_id, relationship_id=relationship_id,
            after_value={"score": score},
        ))
    for target_id in sorted(previous_risks.keys() - current_risks.keys()):
        relationship_id = target_id if target_id in before_relationships else None
        changes.append(DetectedChange(
            "RISK_ASSESSMENT_REMOVED", f"risk-removed:{target_id}",
            entity_id=None if relationship_id else target_id, relationship_id=relationship_id,
            before_value={"score": previous_risks[target_id]},
        ))
    for target_id in sorted(current_risks):
        score = current_risks[target_id]
        before_score = previous_risks.get(target_id)
        crossed_high = score is not None and float(score) >= 75 and (before_score is None or float(before_score) < 75)
        if crossed_high:
            relationship_id = target_id if target_id in after_relationships else None
            changes.append(DetectedChange(
                "NEW_HIGH_RISK_DEPENDENCY", f"high-risk:{target_id}:{float(score):g}",
                entity_id=None if relationship_id else target_id, relationship_id=relationship_id,
                after_value={"score": score},
            ))
    before_factor_hashes = previous.get("risk_factor_hashes", {})
    after_factor_hashes = current.get("risk_factor_hashes", {})
    for target_id in sorted(before_factor_hashes.keys() & after_factor_hashes.keys()):
        if before_factor_hashes[target_id] != after_factor_hashes[target_id]:
            relationship_id = target_id if target_id in after_relationships else None
            changes.append(DetectedChange(
                "RISK_FACTOR_CHANGED", f"risk-factors:{target_id}:{after_factor_hashes[target_id]}",
                entity_id=None if relationship_id else target_id, relationship_id=relationship_id,
                before_value={"factor_hash": before_factor_hashes[target_id]},
                after_value={"factor_hash": after_factor_hashes[target_id]},
            ))
    for target_id in sorted(previous_risks.keys() & current_risks.keys()):
        before, after = previous_risks[target_id], current_risks[target_id]
        if before is None or after is None:
            continue
        difference = float(after) - float(before)
        if difference >= 10:
            change_type = "RISK_INCREASED"
        elif difference <= -10:
            change_type = "RISK_DECREASED"
        else:
            continue
        relationship_id = target_id if target_id in after_relationships else None
        changes.append(DetectedChange(
            change_type, f"risk:{target_id}:{before:g}:{after:g}",
            entity_id=None if relationship_id else target_id, relationship_id=relationship_id,
            before_value={"score": before}, after_value={"score": after},
        ))

    previous_critical = previous.get("critical_dependencies", {})
    current_critical = current.get("critical_dependencies", {})
    for key in sorted(current_critical.keys() - previous_critical.keys()):
        dependency = current_critical[key]
        changes.append(DetectedChange(
            "NEW_CRITICAL_DEPENDENCY", f"critical:{key}",
            entity_id=dependency.get("entity_id"), after_value=dependency,
        ))

    if previous.get("watchlist_state", {}) != current.get("watchlist_state", {}):
        changes.append(DetectedChange(
            "WATCHLIST_CHANGED", "watchlist:" + ",".join(sorted(current.get("watchlist_targets", []))),
            before_value={"watchlist": previous.get("watchlist_state", {})},
            after_value={"watchlist": current.get("watchlist_state", {})},
        ))
    if set(previous.get("alert_state", [])) != set(current.get("alert_state", [])):
        changes.append(DetectedChange(
            "ALERT_STATE_CHANGED", "alerts:" + str(current.get("graph_version", "")),
            before_value={"count": len(previous.get("alert_state", []))},
            after_value={"count": len(current.get("alert_state", []))},
        ))
    return changes


def decide_change(
    change: DetectedChange,
    *,
    watched_target_ids: set[str],
    visited_entity_ids: set[str],
    depth_available: bool,
) -> tuple[str, str, str]:
    """Return decision, concise operational reason, and priority."""
    watched = bool(
        (change.entity_id and change.entity_id in watched_target_ids)
        or (change.relationship_id and change.relationship_id in watched_target_ids)
    )
    priority = "high" if watched or change.change_type in {"NEW_CRITICAL_DEPENDENCY", "VERIFICATION_CONFLICT"} else "normal"
    if change.change_type in {"NEW_ENTITY", "NEW_UPSTREAM_DEPENDENCY", "NEW_CRITICAL_DEPENDENCY"}:
        if change.entity_id and change.entity_id in visited_entity_ids:
            return "NO_ACTION", "This entity is already present in investigation memory; duplicate research was suppressed.", priority
        if not depth_available:
            return "REQUEST_HUMAN_REVIEW", "The configured autonomous depth limit is reached; further research needs human review.", priority
        return "RESEARCH_ENTITY", "A newly persisted dependency needs a bounded follow-up through the existing investigation pipeline.", priority
    if change.change_type in {"NEW_RELATIONSHIP", "RELATIONSHIP_CHANGED", "EVIDENCE_CHANGED"}:
        return "REVERIFY_RELATIONSHIP", "Persisted relationship or evidence state changed; verification should be rerun before risk is trusted.", priority
    if change.change_type == "EVIDENCE_BECAME_STALE":
        if not depth_available:
            return "REQUEST_HUMAN_REVIEW", "Supporting evidence became stale at the autonomous depth limit.", priority
        return "RESEARCH_RELATIONSHIP", "A verified relationship has stale supporting evidence and needs bounded source refresh research.", priority
    if change.change_type in {"RELATIONSHIP_REMOVED", "RISK_ASSESSMENT_ADDED", "RISK_ASSESSMENT_REMOVED", "RISK_INCREASED", "NEW_HIGH_RISK_DEPENDENCY", "RISK_FACTOR_CHANGED", "ENTITY_CHANGED"}:
        before_score = (change.before_value or {}).get("score")
        after_score = (change.after_value or {}).get("score")
        if change.change_type == "RISK_INCREASED" and isinstance(before_score, (int, float)) and isinstance(after_score, (int, float)):
            return "RECALCULATE_RISK", f"Persisted risk increased from {before_score:g} to {after_score:g}/100; recalculate the saved snapshot before acting on it.", priority
        if change.change_type == "RISK_ASSESSMENT_ADDED" and isinstance(after_score, (int, float)):
            return "RECALCULATE_RISK", f"A new persisted risk assessment is {after_score:g}/100; recalculate the snapshot to confirm current exposure.", priority
        if change.change_type == "RISK_ASSESSMENT_REMOVED":
            return "RECALCULATE_RISK", "A persisted risk assessment disappeared from the active snapshot; recalculate risk from current verified state.", priority
        return "RECALCULATE_RISK", "Persisted graph or risk state changed; the saved risk snapshot should be recalculated.", priority
    if change.change_type == "INVESTIGATION_CONFIG_CHANGED":
        return "REQUEST_HUMAN_REVIEW", "Investigation scope or plan changed; an analyst should review the monitoring configuration.", priority
    if change.change_type in {"RISK_DECREASED", "VERIFICATION_CONFLICT"}:
        before_score = (change.before_value or {}).get("score")
        after_score = (change.after_value or {}).get("score")
        if change.change_type == "RISK_DECREASED" and isinstance(before_score, (int, float)) and isinstance(after_score, (int, float)):
            return "REQUEST_HUMAN_REVIEW", f"Persisted risk decreased from {before_score:g} to {after_score:g}/100; an analyst should review the changed evidence and factors.", priority
        return "REQUEST_HUMAN_REVIEW", "A material risk or verification change requires an analyst to review the persisted evidence.", priority
    return "NO_ACTION", "The persisted state changed without requiring an autonomous research or scoring action.", priority
