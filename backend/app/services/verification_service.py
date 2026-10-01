"""Phase 3 orchestration for entity resolution and evidence-backed verification."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.entity_resolution import normalize_name, resolve_entities
from app.agents.verification import verify_relationship
from app.core.database import get_engine
from app.models import Entity, Evidence, Investigation, Relationship


logger = logging.getLogger(__name__)


class VerificationNotReadyError(ValueError):
    pass


class VerificationExecutionError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def verification_state(investigation: Investigation) -> dict[str, Any]:
    return {
        "investigation_id": investigation.id,
        "status": investigation.status,
        "progress": investigation.progress,
        "verification_mode": investigation.verification_mode,
        "verification_progress": investigation.verification_progress,
        "error_message": investigation.error_message,
    }


def start_verification(db: Session, investigation_id: UUID) -> Investigation:
    investigation = db.scalar(
        select(Investigation).where(Investigation.id == investigation_id)
        .with_for_update().execution_options(populate_existing=True)
    )
    if investigation is None:
        raise LookupError("Investigation not found")
    if investigation.status not in {"COMPLETED", "RESEARCH_COMPLETED"}:
        raise VerificationNotReadyError("Research must be completed before verification can start.")
    if investigation.plan is None:
        raise VerificationNotReadyError("Investigation plan is missing.")
    research_progress = investigation.research_progress or {}
    if not research_progress.get("finished_at"):
        raise VerificationNotReadyError("Persisted research completion is required before verification can start.")

    started_at = utc_now()
    mode = "local_demo" if investigation.research_mode == "local_demo" else "deterministic"
    investigation.status = "VERIFYING"
    investigation.progress = max(float(investigation.progress or 0), 90.0)
    investigation.verification_mode = mode
    investigation.verification_progress = {
        "mode": mode,
        "resolution_mode": "deterministic",
        "phase": "entity_resolution",
        "completed_entities": 0,
        "total_entities": 0,
        "canonical_entities": 0,
        "resolved_aliases": 0,
        "possible_duplicates": 0,
        "unresolved_entities": 0,
        "completed_relationships": 0,
        "total_relationships": 0,
        "relationship_candidates": 0,
        "verified_relationships": 0,
        "supported_relationships": 0,
        "conflicted_relationships": 0,
        "rejected_relationships": 0,
        "insufficient_evidence_relationships": 0,
        "started_at": started_at.isoformat(),
        "updated_at": started_at.isoformat(),
        "finished_at": None,
        "message": "Entity resolution is starting.",
        "events": [{"at": started_at.isoformat(), "type": "verification_started", "message": "Deterministic Phase 3 verification started."}],
    }
    investigation.error_message = None
    db.commit()
    db.refresh(investigation)
    return investigation


def run_verification_background(investigation_id: UUID) -> None:
    try:
        with Session(get_engine()) as db:
            execute_verification(db, investigation_id)
    except Exception:
        logger.exception("Unable to complete verification for investigation %s", investigation_id)


def execute_verification(db: Session, investigation_id: UUID, *, evaluated_at: datetime | None = None) -> Investigation:
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise LookupError("Investigation not found")
    if investigation.status != "VERIFYING":
        raise VerificationNotReadyError("Investigation is not in the VERIFYING state.")

    progress = dict(investigation.verification_progress or {})
    evaluated_at = evaluated_at or utc_now()
    try:
        entities = db.scalars(select(Entity).where(Entity.investigation_id == investigation_id).order_by(Entity.created_at, Entity.id)).all()
        relationships = db.scalars(select(Relationship).where(Relationship.investigation_id == investigation_id).order_by(Relationship.created_at, Relationship.id)).all()
        evidence_rows = db.scalars(select(Evidence).where(Evidence.investigation_id == investigation_id).order_by(Evidence.captured_at, Evidence.id)).all()
        sources_by_evidence: dict[str, str] = {str(row.id): row.source for row in evidence_rows}
        plan = investigation.plan or {}
        resolutions = resolve_entities(entities, target_name=plan.get("target") if isinstance(plan, dict) else None)
        entity_by_id = {str(row.id): row for row in entities}
        aliases_by_canonical: dict[str, set[str]] = {}
        sources_by_canonical: dict[str, set[str]] = {}
        evidence_by_canonical: dict[str, set[str]] = {}
        for entity in entities:
            result = resolutions[str(entity.id)]
            metadata = dict(entity.metadata_json or {})
            metadata["normalized_name"] = normalize_name(entity.name)
            metadata["sources"] = sorted({sources_by_evidence[value] for value in result.evidence_ids if value in sources_by_evidence})
            if result.canonical_entity_id and result.canonical_entity_id != str(entity.id):
                state = "RESOLVED_ALIAS"
                aliases_by_canonical.setdefault(result.canonical_entity_id, set()).add(entity.name)
                sources_by_canonical.setdefault(result.canonical_entity_id, set()).update(metadata.get("sources", []))
                evidence_by_canonical.setdefault(result.canonical_entity_id, set()).update(result.evidence_ids)
            elif result.match_type == "POSSIBLE_DUPLICATE":
                state = "POSSIBLE_DUPLICATE"
            elif result.match_type == "UNRESOLVED":
                state = "UNRESOLVED"
            else:
                state = "CANONICAL"
                aliases_by_canonical.setdefault(str(entity.id), set()).update(
                    value for value in (entity.identifiers or []) if isinstance(value, str)
                )
                sources_by_canonical.setdefault(str(entity.id), set()).update(metadata.get("sources", []))
                evidence_by_canonical.setdefault(str(entity.id), set()).update(result.evidence_ids)
            metadata["resolution"] = {
                "mode": "deterministic",
                "status": state,
                "match_type": result.match_type,
                "confidence": result.confidence,
                "canonical_entity_id": result.canonical_entity_id,
                "candidate_entity_id": result.candidate_entity_id,
                "reasons": list(result.reasons),
                "evidence_ids": list(result.evidence_ids),
            }
            metadata["resolution_status"] = state
            metadata["resolution_confidence"] = result.confidence
            metadata["canonical_entity_id"] = result.canonical_entity_id
            entity.metadata_json = metadata

        # All display aliases are retained on the chosen canonical row; original rows and FKs remain intact.
        for canonical_id, aliases in aliases_by_canonical.items():
            canonical = entity_by_id.get(canonical_id)
            if canonical is not None:
                metadata = dict(canonical.metadata_json or {})
                existing = list(metadata.get("aliases") or [])
                metadata["aliases"] = sorted(set(existing) | aliases | {canonical.name})
                metadata["sources"] = sorted(set(metadata.get("sources") or []) | sources_by_canonical.get(canonical_id, set()))
                metadata["source_evidence_ids"] = sorted(set(metadata.get("source_evidence_ids") or []) | evidence_by_canonical.get(canonical_id, set()))
                metadata["canonical_entity_name"] = canonical.name
                canonical.metadata_json = metadata

        canonical_ids = {
            result.canonical_entity_id for result in resolutions.values()
            if result.canonical_entity_id and result.match_type != "UNRESOLVED" and result.match_type != "POSSIBLE_DUPLICATE"
        }
        entity_lookup = {row.id: row for row in entities}
        relationship_groups: dict[tuple[str, str, str], list[Relationship]] = {}
        for relationship in relationships:
            source_resolution = resolutions[str(relationship.source_entity_id)]
            target_resolution = resolutions[str(relationship.target_entity_id)]
            source_id = source_resolution.canonical_entity_id or source_resolution.source_entity_id
            target_id = target_resolution.canonical_entity_id or target_resolution.source_entity_id
            key = (source_id, target_id, relationship.relationship_type.strip().upper())
            relationship_groups.setdefault(key, []).append(relationship)

        progress.update({
            "phase": "relationship_verification", "completed_entities": len(entities), "total_entities": len(entities),
            "canonical_entities": len(canonical_ids),
            "resolved_aliases": sum(result.canonical_entity_id is not None and result.canonical_entity_id != result.source_entity_id for result in resolutions.values()),
            "possible_duplicates": sum(result.match_type == "POSSIBLE_DUPLICATE" for result in resolutions.values()),
            "unresolved_entities": sum(result.match_type == "UNRESOLVED" for result in resolutions.values()),
            "completed_relationships": 0, "total_relationships": len(relationship_groups),
            "relationship_candidates": len(relationships),
            "message": "Entity resolution complete. Relationship verification is starting.",
        })
        _persist_progress(db, investigation, progress)

        evidence_by_relationship: dict[str, list[Evidence]] = {}
        evidence_by_id = {str(row.id): row for row in evidence_rows}
        for evidence in evidence_rows:
            if evidence.relationship_id:
                evidence_by_relationship.setdefault(str(evidence.relationship_id), []).append(evidence)
        statuses = {
            "VERIFIED": "verified_relationships", "SUPPORTED": "supported_relationships",
            "CONFLICTED": "conflicted_relationships", "REJECTED": "rejected_relationships",
            "INSUFFICIENT_EVIDENCE": "insufficient_evidence_relationships",
        }
        for index, (candidate_key, candidate_rows) in enumerate(relationship_groups.items(), start=1):
            source = entity_by_id.get(candidate_key[0])
            target = entity_by_id.get(candidate_key[1])
            if source is None or target is None:
                raise ValueError("Relationship endpoints are missing from the investigation.")
            linked_by_id: dict[str, Evidence] = {}
            for relationship in candidate_rows:
                for evidence in evidence_by_relationship.get(str(relationship.id), []):
                    linked_by_id[str(evidence.id)] = evidence
                metadata = relationship.metadata_json or {}
                for evidence_id in metadata.get("source_evidence_ids", []):
                    linked_evidence = evidence_by_id.get(str(evidence_id))
                    if linked_evidence is not None:
                        linked_by_id[str(linked_evidence.id)] = linked_evidence
            linked = list(linked_by_id.values())
            extraction_values = [float(row.confidence) for row in candidate_rows if isinstance(row.confidence, (int, float))]
            extraction_confidence = max(extraction_values) if extraction_values else None
            representative = SimpleNamespace(
                id=candidate_rows[0].id, relationship_type=candidate_rows[0].relationship_type,
                confidence=extraction_confidence, confidence_score=extraction_confidence,
            )
            result = verify_relationship(representative, source, target, linked, evaluated_at=evaluated_at)
            verification_data = {
                "mode": progress.get("mode", "deterministic"), "resolution_mode": "deterministic",
                "status": result.status, "confidence": result.confidence,
                "verified_at": result.verified_at.isoformat() if result.verified_at else None,
                "evaluated_at": evaluated_at.isoformat(),
                "evidence_ids": list(result.evidence_ids),
                "supporting_evidence_ids": list(result.supporting_evidence),
                "conflicting_evidence_ids": list(result.conflicting_evidence),
                "candidate_relationship_ids": [str(row.id) for row in candidate_rows],
                "explanation": result.explanation, **result.details,
            }
            canonical_relationship_id = str(candidate_rows[0].id)
            for relationship in candidate_rows:
                relationship.verification_status = result.status
                relationship.confidence = result.confidence
                relationship.confidence_score = result.confidence
                relationship.metadata_json = {
                    **dict(relationship.metadata_json or {}),
                    "canonical_relationship_id": canonical_relationship_id,
                    "verification": verification_data,
                }
            for evidence in linked:
                score = next((row for row in result.details["evidence_scores"] if row["evidence_id"] == str(evidence.id)), None)
                if score:
                    evidence.verification_status = score["classification"]
            progress[statuses[result.status]] = int(progress.get(statuses[result.status], 0)) + 1
            progress["completed_relationships"] = index
            progress["phase"] = "relationship_verification"
            progress["message"] = f"Verified relationship candidate {index} of {len(relationship_groups)}."
            _persist_progress(db, investigation, progress)

        finished_at = utc_now()
        progress.update({
            "phase": "complete", "finished_at": finished_at.isoformat(), "updated_at": finished_at.isoformat(),
            "message": "Verification completed. Risk analysis has not started.",
        })
        investigation.verification_mode = progress.get("mode", "deterministic")
        investigation.verification_progress = dict(progress)
        investigation.status = "VERIFICATION_COMPLETED"
        investigation.progress = 100.0
        investigation.error_message = None
        db.commit()
        db.refresh(investigation)
        return investigation
    except Exception as exc:
        db.rollback()
        failed = db.get(Investigation, investigation_id)
        if failed is not None:
            failed.status = "FAILED"
            failed.error_message = "Verification could not be completed."
            failed_progress = dict(failed.verification_progress or progress)
            failed_progress.update({"phase": "failed", "updated_at": utc_now().isoformat(), "finished_at": utc_now().isoformat(), "message": failed.error_message})
            failed.verification_progress = failed_progress
            db.commit()
        raise VerificationExecutionError("Verification could not be completed.") from exc


def _persist_progress(db: Session, investigation: Investigation, progress: dict[str, Any]) -> None:
    progress["updated_at"] = utc_now().isoformat()
    investigation.verification_progress = dict(progress)
    db.commit()
