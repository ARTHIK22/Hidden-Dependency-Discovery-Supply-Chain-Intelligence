"""Risk-analysis orchestration, persistence, and lifecycle state transitions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_engine
from app.models import Entity, Evidence, Investigation, Relationship, Risk
from risk_engine import EvidenceRecord, EntityRecord, RelationshipRecord, calculate_risk
from app.services.alert_service import evaluate_risk_alerts


logger = logging.getLogger(__name__)


class RiskAnalysisNotReadyError(ValueError):
    pass


class RiskAnalysisInProgressError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def risk_state(investigation: Investigation) -> dict[str, Any]:
    analysis = investigation.risk_analysis or {}
    return {
        "investigation_id": str(investigation.id),
        "status": investigation.status,
        "progress": investigation.progress,
        "risk_progress": investigation.risk_progress,
        "risk_analysis": analysis,
        "error_message": investigation.error_message,
    }


def start_risk_analysis(db: Session, investigation: Investigation) -> Investigation:
    investigation = db.scalar(
        select(Investigation).where(Investigation.id == investigation.id)
        .with_for_update().execution_options(populate_existing=True)
    )
    if investigation is None:
        raise LookupError("Investigation not found")
    if investigation.demo_mode:
        raise RiskAnalysisNotReadyError("Illustrative demo investigations are not eligible for calculated risk analysis.")
    if investigation.status == "RISK_ANALYZING":
        raise RiskAnalysisInProgressError("Risk analysis is already in progress.")
    if investigation.status not in {"VERIFICATION_COMPLETED", "RISK_ANALYZED", "COMPLETED"}:
        raise RiskAnalysisNotReadyError("Relationship verification must be complete before risk analysis.")
    verification = investigation.verification_progress or {}
    if not verification.get("finished_at"):
        raise RiskAnalysisNotReadyError("Persisted verification completion is required before risk analysis.")

    started_at = utc_now()
    investigation.status = "RISK_ANALYZING"
    investigation.progress = max(float(investigation.progress or 0), 92.0)
    investigation.error_message = None
    investigation.risk_progress = {
        "mode": "deterministic",
        "phase": "graph_scoring",
        "started_at": started_at.isoformat(),
        "updated_at": started_at.isoformat(),
        "finished_at": None,
        "message": "Calculating explainable risk from verified relationships and persisted evidence.",
        "entities_scored": 0,
        "relationships_scored": 0,
        "events": [{"at": started_at.isoformat(), "type": "risk_analysis_started", "message": "Risk analysis started."}],
    }
    _append_event(investigation, "risk_analysis_started", "Risk analysis started.", started_at)
    db.commit()
    db.refresh(investigation)
    return investigation


def run_risk_analysis_background(investigation_id: UUID) -> None:
    try:
        with Session(get_engine()) as db:
            execute_risk_analysis(db, investigation_id)
    except Exception:
        logger.exception("Risk analysis failed for investigation %s", investigation_id)


def execute_risk_analysis(db: Session, investigation_id: UUID, *, as_of: datetime | None = None) -> Investigation:
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise LookupError("Investigation not found")
    if investigation.status != "RISK_ANALYZING":
        raise RiskAnalysisNotReadyError("Investigation is not in the RISK_ANALYZING state.")

    try:
        entities = db.scalars(
            select(Entity).where(Entity.investigation_id == investigation_id).order_by(Entity.id)
        ).all()
        relationships = db.scalars(
            select(Relationship).where(Relationship.investigation_id == investigation_id).order_by(Relationship.id)
        ).all()
        relationship_ids = [row.id for row in relationships]
        evidence_rows = []
        if relationship_ids:
            evidence_rows = db.scalars(
                select(Evidence)
                .where(or_(
                    Evidence.investigation_id == investigation_id,
                    Evidence.relationship_id.in_(relationship_ids),
                ))
                .order_by(Evidence.id)
            ).all()
        supporting_evidence = {
            row.id: _supporting_evidence_ids(row.metadata_json or {})
            for row in relationships
        }

        plan = investigation.plan or {}
        result = calculate_risk(
            [EntityRecord(
                id=str(row.id), name=row.name, entity_type=row.entity_type,
                jurisdiction=row.jurisdiction, metadata=row.metadata_json or {},
            ) for row in entities],
            [RelationshipRecord(
                id=str(row.id), source_id=str(row.source_entity_id), target_id=str(row.target_entity_id),
                relationship_type=row.relationship_type,
                verification_status=row.verification_status,
                # `confidence_score` is a legacy column defaulted to 0.0, so it
                # cannot distinguish an unknown confidence from a measured zero.
                confidence=row.confidence,
                metadata=row.metadata_json or {},
            ) for row in relationships],
            [EvidenceRecord(
                id=str(row.id), relationship_id=str(row.relationship_id or ""), source=row.source,
                source_type=row.source_type, published_date=row.published_date,
                metadata=row.metadata_json or {},
            ) for row in evidence_rows
                if row.relationship_id is not None
                and str(row.id) in supporting_evidence.get(row.relationship_id, set())],
            target_name=plan.get("target"),
            as_of=as_of,
        )

        snapshot_id = uuid4()
        calculated_at = utc_now()
        previous = investigation.risk_analysis or {}
        summary = dict(result.summary)
        report_snapshot = result.as_dict()
        report_snapshot["snapshot_id"] = str(snapshot_id)
        report_snapshot["calculated_at"] = calculated_at.isoformat()
        report_snapshot["previous_snapshot_id"] = previous.get("snapshot_id")

        entity_by_id = {str(row.id): row for row in entities}
        for assessment in result.entity_risks:
            entity = entity_by_id[assessment.target_id]
            entity.risk_score = assessment.score
            entity.risk_level = assessment.level
            db.add(Risk(
                entity_id=entity.id,
                investigation_id=investigation.id,
                score=assessment.score,
                score_scale="percent",
                level=assessment.level,
                reason=assessment.reason,
                risk_type="entity_exposure",
                severity=assessment.level.lower(),
                title=f"{entity.name} risk assessment",
                snapshot_id=snapshot_id,
                local_score=None if assessment.score is None else max(0.0, assessment.score - (assessment.propagated_score or 0.0)),
                propagated_score=assessment.propagated_score,
                risk_factors=[factor.as_dict() for factor in assessment.factors],
            ))

        relationship_by_id = {str(row.id): row for row in relationships}
        for assessment in result.relationship_risks:
            relation = relationship_by_id[assessment.target_id]
            db.add(Risk(
                entity_id=relation.source_entity_id,
                investigation_id=investigation.id,
                relationship_id=relation.id,
                score=assessment.score,
                score_scale="percent",
                level=assessment.level,
                reason=assessment.reason,
                risk_type="relationship_exposure",
                severity=assessment.level.lower(),
                title=f"{relation.relationship_type} relationship risk",
                snapshot_id=snapshot_id,
                local_score=assessment.score,
                propagated_score=None,
                risk_factors=[factor.as_dict() for factor in assessment.factors],
            ))

        created_alerts = evaluate_risk_alerts(
            db, investigation, result, snapshot_id=snapshot_id, relationships=relationships,
        )
        events = list(investigation.lifecycle_events or [])
        for assessment in (*result.entity_risks, *result.relationship_risks):
            events.append({
                "id": str(uuid4()), "at": calculated_at.isoformat(), "type": "risk_factor_calculated",
                "message": f"{assessment.target_type} risk factors calculated ({assessment.level}).",
                "target_type": assessment.target_type, "target_id": assessment.target_id,
            })
        for dependency in result.critical_dependencies:
            events.append({
                "id": str(uuid4()), "at": calculated_at.isoformat(), "type": "critical_dependency_detected",
                "message": str(dependency["explanation"]), "dependency_type": str(dependency["type"]),
            })
        for alert in created_alerts:
            events.append({
                "id": str(uuid4()), "at": alert.created_at.isoformat(), "type": "alert_created",
                "message": alert.title, "alert_id": str(alert.id),
            })

        completed_at = utc_now()
        events.append({
            "id": str(uuid4()), "at": completed_at.isoformat(), "type": "risk_analysis_completed",
            "message": "Risk analysis completed using persisted verified-graph data.",
        })
        investigation.lifecycle_events = events[-200:]
        investigation.risk_analysis = report_snapshot
        investigation.risk_progress = {
            "mode": "deterministic",
            "phase": "completed",
            "started_at": (investigation.risk_progress or {}).get("started_at"),
            "updated_at": completed_at.isoformat(),
            "finished_at": completed_at.isoformat(),
            "message": "Risk analysis completed. Unknown factors and conflicts remain explicitly recorded.",
            "entities_scored": summary["entities_scored"],
            "relationships_scored": len(result.relationship_risks),
            "events": [{"at": item["at"], "type": item["type"], "message": item["message"]} for item in events[-40:]],
        }
        investigation.status = "RISK_ANALYZED"
        investigation.progress = 98.0
        investigation.error_message = None
        db.commit()
        db.refresh(investigation)
        return investigation
    except Exception as exc:
        db.rollback()
        failed = db.get(Investigation, investigation_id)
        if failed is not None:
            failed.status = "FAILED"
            failed.error_message = "Risk analysis failed. Existing verified data and prior snapshots were preserved."
            failed.risk_progress = {
                **(failed.risk_progress or {}),
                "phase": "failed",
                "updated_at": utc_now().isoformat(),
                "finished_at": utc_now().isoformat(),
                "message": failed.error_message,
            }
            _append_event(failed, "investigation_failed", failed.error_message)
            db.commit()
        logger.exception("Risk analysis execution failed for investigation %s", investigation_id)
        raise RuntimeError("Risk analysis failed") from exc


def _append_event(
    investigation: Investigation,
    event_type: str,
    message: str,
    at: datetime | None = None,
) -> None:
    events = list(investigation.lifecycle_events or [])
    events.append({"id": str(uuid4()), "at": (at or utc_now()).isoformat(), "type": event_type, "message": message})
    investigation.lifecycle_events = events[-200:]


def _supporting_evidence_ids(metadata: dict[str, Any]) -> set[str]:
    verification = metadata.get("verification", {}) if isinstance(metadata, dict) else {}
    if not isinstance(verification, dict):
        return set()
    values = verification.get("supporting_evidence_ids", [])
    return {str(value) for value in values} if isinstance(values, (list, tuple, set)) else set()
