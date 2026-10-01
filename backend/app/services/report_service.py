"""Persisted-data investigation report assembly."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Alert, Entity, Evidence, Investigation, Relationship, Report, Risk


def generate_investigation_report(
    db: Session,
    investigation: Investigation,
    *,
    generated_at: datetime | None = None,
) -> Report:
    started_at = datetime.now(timezone.utc)
    _append_event(investigation, "report_generation_started", "Report generation started.", started_at)
    generated_at = generated_at or datetime.now(timezone.utc)
    completed_at = generated_at

    entities = db.scalars(
        select(Entity).where(Entity.investigation_id == investigation.id).order_by(Entity.name, Entity.id)
    ).all()
    relationships = db.scalars(
        select(Relationship).where(Relationship.investigation_id == investigation.id).order_by(Relationship.id)
    ).all()
    relationship_ids = [row.id for row in relationships]
    evidence_rows = []
    if relationship_ids:
        evidence_rows = db.scalars(
            select(Evidence).where(or_(
                Evidence.investigation_id == investigation.id,
                Evidence.relationship_id.in_(relationship_ids),
            )).order_by(Evidence.published_date, Evidence.captured_at, Evidence.id)
        ).all()
    risk_rows = db.scalars(
        select(Risk).where(Risk.investigation_id == investigation.id).order_by(Risk.created_at, Risk.id)
    ).all()
    alert_rows = db.scalars(
        select(Alert).where(Alert.investigation_id == investigation.id).order_by(Alert.created_at, Alert.id)
    ).all()

    entity_by_id = {row.id: row for row in entities}
    evidence_by_relationship: dict[UUID, list[dict[str, Any]]] = {}
    evidence_data = []
    source_data: dict[str, dict[str, Any]] = {}
    for row in evidence_rows:
        item = {
            "id": str(row.id), "relationship_id": None if row.relationship_id is None else str(row.relationship_id),
            "title": row.title, "source": row.source, "source_type": row.source_type,
            "source_url": row.source_url, "published_date": _iso(row.published_date),
            "captured_at": _iso(row.captured_at), "confidence": row.confidence,
            "verification_status": row.verification_status, "excerpt": row.excerpt,
            "metadata": row.metadata_json or {},
            "demo_only": bool((row.metadata_json or {}).get("demo_only") or "DEMO" in row.source.upper()),
        }
        evidence_data.append(item)
        if row.relationship_id is not None:
            evidence_by_relationship.setdefault(row.relationship_id, []).append(item)
        source_data.setdefault(row.source, {
            "source": row.source, "source_type": row.source_type, "source_url": row.source_url,
            "evidence_count": 0, "demo_only": item["demo_only"],
        })["evidence_count"] += 1

    entity_data = [{
        "id": str(row.id), "name": row.name, "entity_type": row.entity_type,
        "description": row.description, "jurisdiction": row.jurisdiction,
        "identifiers": row.identifiers or [], "metadata": row.metadata_json or {},
        "resolution": _resolution_data(row.metadata_json or {}),
        "demo_only": investigation.demo_mode or "DEMO" in (row.description or "").upper(),
    } for row in entities]
    relationship_data = []
    unknowns: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    verification_counts: dict[str, int] = {}
    for row in relationships:
        status = row.verification_status.upper()
        verification_counts[status] = verification_counts.get(status, 0) + 1
        metadata = row.metadata_json or {}
        verification = metadata.get("verification", {}) if isinstance(metadata, dict) else {}
        source_entity = entity_by_id.get(row.source_entity_id)
        target_entity = entity_by_id.get(row.target_entity_id)
        item = {
            "id": str(row.id), "source_entity_id": str(row.source_entity_id),
            "source_entity": source_entity.name if source_entity else None,
            "target_entity_id": str(row.target_entity_id),
            "target_entity": target_entity.name if target_entity else None,
            "relationship_type": row.relationship_type, "verification_status": status,
            "confidence": row.confidence, "evidence_summary": row.evidence_summary,
            "metadata": metadata, "evidence": evidence_by_relationship.get(row.id, []),
            "demo_only": investigation.demo_mode or "DEMO" in (row.source or "").upper(),
        }
        relationship_data.append(item)
        if status in {"UNKNOWN", "INSUFFICIENT_EVIDENCE", "POSSIBLE_DUPLICATE", "UNRESOLVED"}:
            unknowns.append({
                "kind": "relationship", "id": str(row.id), "status": status,
                "reason": (verification.get("explanation") if isinstance(verification, dict) else None) or row.evidence_summary or "Relationship state is unresolved.",
            })
        if status == "CONFLICTED":
            conflicts.append({
                "relationship_id": str(row.id), "relationship_type": row.relationship_type,
                "supporting_evidence_ids": verification.get("supporting_evidence_ids", []) if isinstance(verification, dict) else [],
                "conflicting_evidence_ids": verification.get("conflicting_evidence_ids", []) if isinstance(verification, dict) else [],
                "reason": verification.get("explanation") if isinstance(verification, dict) else row.evidence_summary,
            })

    for row in entities:
        resolution = _resolution_data(row.metadata_json or {})
        if resolution.get("status") in {"UNRESOLVED", "POSSIBLE_DUPLICATE"}:
            unknowns.append({"kind": "entity", "id": str(row.id), "status": resolution["status"], "reason": resolution.get("reason")})

    analysis = investigation.risk_analysis or {}
    summary = analysis.get("summary", {}) if isinstance(analysis, dict) else {}
    risk_snapshot = analysis.get("entity_risks", []) + analysis.get("relationship_risks", []) if isinstance(analysis, dict) else []
    for assessment in risk_snapshot:
        if isinstance(assessment, dict):
            for factor in assessment.get("factors", []):
                if isinstance(factor, dict) and factor.get("status") == "UNKNOWN":
                    unknowns.append({
                        "kind": "risk_factor", "target_type": assessment.get("target_type"),
                        "target_id": assessment.get("target_id"), "factor": factor.get("key"),
                        "reason": factor.get("explanation"),
                    })

    plan = investigation.plan or {}
    if plan.get("target") is None:
        unknowns.append({
            "kind": "investigation_target", "status": "UNRESOLVED",
            "reason": plan.get("target_clarification") or "The goal did not identify one unambiguous organization or product target.",
        })

    if investigation.status == "RISK_ANALYZED":
        investigation.status = "COMPLETED"
        investigation.progress = 100.0
        _append_event(investigation, "investigation_completed", "Investigation lifecycle completed.", completed_at)
    _append_event(investigation, "report_generation_completed", "Report was generated from persisted investigation data.", completed_at)

    report_data: dict[str, Any] = {
        "schema_version": "hdi-investigation-report-v1",
        "generated_at": _iso(generated_at),
        "demo_only": bool(investigation.demo_mode),
        "investigation": {
            "id": str(investigation.id), "name": investigation.name, "goal": investigation.goal,
            "objective": investigation.objective, "status": investigation.status,
            "progress": investigation.progress, "depth": investigation.depth,
            "scope": investigation.scope or {}, "created_at": _iso(investigation.created_at),
            "updated_at": _iso(investigation.updated_at),
        },
        "plan": plan,
        "research": {"mode": investigation.research_mode, "progress": investigation.research_progress},
        "sources": sorted(source_data.values(), key=lambda item: str(item["source"]).casefold()),
        "evidence": evidence_data,
        "entities": entity_data,
        "entity_resolution": [item["resolution"] | {"entity_id": item["id"], "entity_name": item["name"]} for item in entity_data],
        "relationships": relationship_data,
        "verification": {
            "mode": investigation.verification_mode,
            "progress": investigation.verification_progress,
            "status_counts": verification_counts,
            "confidence_values": [{"relationship_id": item["id"], "confidence": item["confidence"]} for item in relationship_data],
        },
        "dependency_graph": {
            "entity_count": len(entity_data), "relationship_count": len(relationship_data),
            "verified_count": verification_counts.get("VERIFIED", 0),
            "conflicted_count": verification_counts.get("CONFLICTED", 0),
        },
        "risk": {
            "summary": summary, "snapshot_id": analysis.get("snapshot_id") if isinstance(analysis, dict) else None,
            "calculated_at": analysis.get("calculated_at") if isinstance(analysis, dict) else None,
            "assessments": risk_snapshot,
            "critical_dependencies": analysis.get("critical_dependencies", []) if isinstance(analysis, dict) else [],
            "record_count": len(risk_rows),
        },
        "alerts": [{
            "id": str(row.id), "type": row.alert_type, "title": row.title, "message": row.message,
            "severity": row.severity, "entity_id": None if row.entity_id is None else str(row.entity_id),
            "relationship_id": None if row.relationship_id is None else str(row.relationship_id),
            "risk_score": row.risk_score, "reason": row.reason,
            "evidence_ids": row.evidence_ids or [], "created_at": _iso(row.created_at),
            "demo_only": row.owner_id is None and investigation.demo_mode,
        } for row in alert_rows],
        "unknowns": unknowns,
        "conflicts": conflicts,
        "timeline": list(investigation.lifecycle_events or []),
    }
    content = _render_report(report_data)
    report = Report(
        investigation_id=investigation.id,
        title=f"{investigation.name} — Investigation Report",
        content=content,
        structured_content=report_data,
    )
    db.add(report)
    db.flush()
    db.commit()
    db.refresh(report)
    return report


def _resolution_data(metadata: dict[str, Any]) -> dict[str, Any]:
    status = metadata.get("resolution_status") or metadata.get("entity_resolution_status")
    resolution = metadata.get("resolution")
    if isinstance(resolution, dict):
        status = status or resolution.get("status")
        return {"status": status or "UNKNOWN", **resolution}
    return {
        "status": status or "UNKNOWN",
        "canonical_entity_id": metadata.get("canonical_entity_id"),
        "aliases": metadata.get("aliases", []),
        "confidence": metadata.get("resolution_confidence"),
        "reason": metadata.get("resolution_reason"),
    }


def _render_report(data: dict[str, Any]) -> str:
    investigation = data["investigation"]
    risk = data["risk"]["summary"]
    lines = [
        "# Hidden Dependency Discovery — Investigation Report",
        "",
        f"**Investigation:** {investigation['name']}",
        f"**Goal:** {investigation['goal']}",
        f"**Status:** {investigation['status']}",
        f"**Generated:** {data['generated_at']}",
        f"**Demo only:** {'Yes — illustrative data' if data['demo_only'] else 'No'}",
        "",
        "## Persisted data summary",
        f"- Sources: {len(data['sources'])}",
        f"- Evidence records: {len(data['evidence'])}",
        f"- Entities: {len(data['entities'])}",
        f"- Relationships: {len(data['relationships'])}",
        f"- Verified relationships: {data['dependency_graph']['verified_count']}",
        f"- Conflicted relationships: {data['dependency_graph']['conflicted_count']}",
        f"- Risk score: {risk.get('overall_score', 'UNKNOWN')}/100 ({risk.get('overall_level', 'UNKNOWN')})",
        f"- Alerts: {len(data['alerts'])}",
        f"- Unresolved items: {len(data['unknowns'])}",
        "",
        "## Findings",
        "Content below is taken from persisted application records. Missing or conflicting facts remain marked as such.",
        "",
    ]
    if data["relationships"]:
        for relation in data["relationships"]:
            lines.append(
                f"- {relation.get('source_entity') or 'Unknown'} —{relation['relationship_type']}→ "
                f"{relation.get('target_entity') or 'Unknown'} [{relation['verification_status']}; confidence {relation.get('confidence') if relation.get('confidence') is not None else 'UNKNOWN'}]"
            )
    else:
        lines.append("No relationship records are available.")
    lines.extend(["", "## Unknowns and conflicts"])
    if data["unknowns"]:
        lines.extend(f"- {item.get('kind')}: {item.get('reason') or item.get('status') or item.get('factor')}" for item in data["unknowns"])
    else:
        lines.append("No unresolved records were present at report generation time.")
    if data["conflicts"]:
        lines.extend(f"- Conflict on {item['relationship_type']} relationship {item['relationship_id']}: {item.get('reason') or 'conflicting evidence preserved'}" for item in data["conflicts"])
    lines.extend(["", "## Limitations", "This report contains persisted records only. It does not infer missing suppliers, sources, or evidence."])
    return "\n".join(lines)


def _append_event(investigation: Investigation, event_type: str, message: str, at: datetime) -> None:
    events = list(investigation.lifecycle_events or [])
    events.append({"id": str(uuid4()), "at": at.isoformat(), "type": event_type, "message": message})
    investigation.lifecycle_events = events[-200:]


def _iso(value: datetime | Any | None) -> str | None:
    return value.isoformat() if value is not None else None
