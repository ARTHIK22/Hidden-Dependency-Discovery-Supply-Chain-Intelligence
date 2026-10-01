"""Persisted monitoring runs, deterministic decisions, and bounded follow-ups."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.agents.monitoring.decision_engine import DetectedChange, decide_change, detect_changes
from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.agents.schemas import InvestigationPlan
from app.core.config import settings
from app.core.database import get_engine
from app.models import (
    AgentDecision,
    Alert,
    Entity,
    Evidence,
    Investigation,
    InvestigationChange,
    MonitoringConfig,
    MonitoringRun,
    MonitoringSnapshot,
    Relationship,
    Risk,
    WatchlistEntry,
)
from app.schemas.investigation import InvestigationCreate
from app.services.investigation_service import create_planned_investigation
from app.services.alert_service import create_monitoring_alert
from app.services.research_service import build_research_provider, execute_research, start_research
from app.services.risk_service import execute_risk_analysis, start_risk_analysis
from app.services.verification_service import execute_verification, start_verification
from risk_engine import RelationshipRecord, dependency_orientation


logger = logging.getLogger(__name__)
MAX_FOLLOWUPS_PER_RUN = 3
MAX_AUTONOMOUS_DEPTH = 3
DEPTH_BY_LABEL = {"standard": 1, "deep": 2, "maximum": 3}
SUPPORTED_DECISIONS = {
    "NO_ACTION",
    "RESEARCH_ENTITY",
    "RESEARCH_RELATIONSHIP",
    "REVERIFY_RELATIONSHIP",
    "RECALCULATE_RISK",
    "CREATE_ALERT",
    "REQUEST_HUMAN_REVIEW",
}


class MonitoringNotReadyError(ValueError):
    pass


class MonitoringDisabledError(ValueError):
    pass


class MonitoringInProgressError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def enable_monitoring(db: Session, investigation: Investigation, interval_minutes: int | None = None) -> MonitoringConfig:
    investigation = db.scalar(
        select(Investigation).where(Investigation.id == investigation.id)
        .with_for_update().execution_options(populate_existing=True)
    )
    if investigation is None:
        raise LookupError("Investigation not found")
    if investigation.demo_mode:
        raise MonitoringNotReadyError("Illustrative demo investigations cannot be autonomously monitored.")
    if investigation.plan is None or not (investigation.verification_progress or {}).get("finished_at"):
        raise MonitoringNotReadyError("Research and verification must be complete before monitoring can be enabled.")
    if investigation.status in {"PLANNING", "RESEARCHING", "VERIFYING", "RISK_ANALYZING"}:
        raise MonitoringNotReadyError("Monitoring cannot be enabled while an investigation pipeline step is running.")

    interval = interval_minutes or settings.monitoring_default_interval_minutes
    interval = max(settings.monitoring_min_interval_minutes, min(settings.monitoring_max_interval_minutes, int(interval)))
    now = utc_now()
    config = db.get(MonitoringConfig, investigation.id)
    if config is not None and config.status == "MONITORING_RUNNING":
        raise MonitoringNotReadyError("Monitoring cannot be reset while a monitoring run is in progress.")
    if config is None:
        config = MonitoringConfig(investigation_id=investigation.id)
        db.add(config)
        db.flush()

    config.enabled = True
    config.status = "MONITORING_ENABLED"
    config.interval_minutes = interval
    config.max_autonomous_depth = _max_depth(investigation)
    config.enabled_at = now
    config.next_check_at = now + timedelta(minutes=interval)
    config.last_error = None
    config.memory_json = _seed_memory(db, investigation, config.memory_json or {})
    state = _capture_state(db, investigation, config, as_of=now)
    snapshot = MonitoringSnapshot(
        investigation_id=investigation.id,
        graph_version=state["graph_version"],
        state_json=state,
        entity_count=len(state["entities"]),
        relationship_count=len(state["relationships"]),
        evidence_count=len(state["evidence"]),
    )
    db.add(snapshot)
    db.flush()
    config.latest_snapshot_id = snapshot.id
    _append_event(investigation, "monitoring_enabled", f"Continuous monitoring enabled with a {interval}-minute interval.")
    db.commit()
    db.refresh(config)
    return config


def disable_monitoring(db: Session, investigation: Investigation) -> MonitoringConfig:
    config = db.get(MonitoringConfig, investigation.id)
    if config is not None and config.status == "MONITORING_RUNNING":
        raise MonitoringInProgressError("Wait for the active monitoring run to finish before disabling monitoring.")
    if config is None:
        config = MonitoringConfig(investigation_id=investigation.id)
        db.add(config)
    config.enabled = False
    config.status = "MONITORING_DISABLED"
    config.next_check_at = None
    config.run_started_at = None
    config.last_error = None
    _append_event(investigation, "monitoring_disabled", "Continuous monitoring disabled by the investigation owner.")
    db.commit()
    db.refresh(config)
    return config


def queue_monitoring_run(db: Session, investigation: Investigation, *, scheduled: bool = False) -> MonitoringRun:
    investigation = db.scalar(
        select(Investigation).where(Investigation.id == investigation.id)
        .with_for_update().execution_options(populate_existing=True)
    )
    if investigation is None:
        raise LookupError("Investigation not found")
    config = db.get(MonitoringConfig, investigation.id, with_for_update=True)
    if config is None or not config.enabled:
        raise MonitoringDisabledError("Enable monitoring before starting a monitoring run.")
    now = utc_now()
    if scheduled and (config.next_check_at is None or _aware(config.next_check_at) > now):
        raise MonitoringDisabledError("The next scheduled monitoring interval has not arrived.")
    if investigation.status in {"QUEUED", "PLANNING", "PLANNED", "RESEARCHING", "VERIFYING", "RISK_ANALYZING"}:
        if scheduled:
            config.next_check_at = now + timedelta(minutes=config.interval_minutes)
            db.commit()
        raise MonitoringInProgressError("Wait for the investigation pipeline to finish before monitoring it.")
    if config.status == "MONITORING_RUNNING" and config.run_started_at is not None:
        started = _aware(config.run_started_at)
        if now - started < timedelta(minutes=max(5, config.interval_minutes * 2)):
            raise MonitoringInProgressError("A monitoring run is already in progress.")
        abandoned = db.scalar(select(MonitoringRun).where(
            MonitoringRun.investigation_id == investigation.id,
            MonitoringRun.status == "MONITORING_RUNNING",
        ).order_by(MonitoringRun.started_at.desc()).limit(1))
        if abandoned is not None:
            abandoned.status = "MONITORING_FAILED"
            abandoned.finished_at = now
            abandoned.error_message = "The previous worker stopped before recording a completed scan."
        _append_event(investigation, "monitoring_failed", "An abandoned monitoring run was closed after its safety timeout.")

    previous_id = config.latest_snapshot_id
    run = MonitoringRun(
        investigation_id=investigation.id,
        status="MONITORING_RUNNING",
        started_at=now,
        previous_snapshot_id=previous_id,
    )
    db.add(run)
    config.status = "MONITORING_RUNNING"
    config.run_started_at = now
    config.last_error = None
    _append_event(investigation, "monitoring_started", "Persisted investigation state is being checked for changes.")
    db.commit()
    db.refresh(run)
    return run


def run_monitoring_background(run_id: UUID) -> None:
    try:
        with Session(get_engine()) as db:
            execute_monitoring_run(db, run_id)
    except Exception:
        logger.exception("Unable to open a monitoring session for run %s", run_id)


def execute_monitoring_run(db: Session, run_id: UUID, *, as_of: datetime | None = None) -> MonitoringRun:
    run = db.get(MonitoringRun, run_id)
    if run is None:
        raise LookupError("Monitoring run not found")
    if run.status != "MONITORING_RUNNING":
        return run
    investigation = db.get(Investigation, run.investigation_id)
    config = db.get(MonitoringConfig, run.investigation_id)
    if investigation is None or config is None:
        raise LookupError("Monitoring configuration not found")

    checked_at = as_of or utc_now()
    try:
        previous_snapshot = db.get(MonitoringSnapshot, run.previous_snapshot_id) if run.previous_snapshot_id else None
        previous_state = previous_snapshot.state_json if previous_snapshot is not None else None
        before_actions = _capture_state(db, investigation, config, as_of=checked_at)
        detected = detect_changes(previous_state, before_actions)
        change_rows: list[InvestigationChange] = []
        change_rows_by_key: dict[str, InvestigationChange] = {}
        for change in detected:
            row = _persist_change(db, investigation, run, change, previous_state, before_actions)
            if row is not None:
                change_rows.append(row)
                change_rows_by_key[change.change_key] = row
                _append_event(
                    investigation,
                    "change_detected",
                    f"{change.change_type.replace('_', ' ').title()} detected from persisted investigation state.",
                    change_id=str(row.id), entity_id=change.entity_id, relationship_id=change.relationship_id,
                )

        memory = dict(config.memory_json or {})
        watched = _watched_ids(before_actions)
        depth_available = _current_autonomous_depth(investigation) < config.max_autonomous_depth
        decisions: list[AgentDecision] = []
        changes_for_decision = detected
        if not changes_for_decision:
            changes_for_decision = [DetectedChange(
                "NO_CHANGE", f"no-change:{before_actions['graph_version']}",
                after_value={"graph_version": before_actions["graph_version"]},
            )]

        for change in changes_for_decision:
            watched_for_change = set(watched)
            if str(investigation.id) in watched:
                watched_for_change.update(value for value in (change.entity_id, change.relationship_id) if value)
            decision_name, reason, priority = decide_change(
                change,
                watched_target_ids=watched_for_change,
                visited_entity_ids=set(memory.get("visited_entity_ids", [])),
                depth_available=depth_available,
            )
            if decision_name not in SUPPORTED_DECISIONS:
                decision_name = "REQUEST_HUMAN_REVIEW"
                reason = "The event requires analyst review because it has no safe autonomous action."
            if change.change_type == "NO_CHANGE":
                decision_name = "NO_ACTION"
                reason = "No persisted graph, evidence, verification, risk, watchlist, or alert state changed since the previous snapshot."

            depth_limited = (
                not depth_available
                and change.change_type in {
                    "NEW_ENTITY", "NEW_UPSTREAM_DEPENDENCY", "NEW_CRITICAL_DEPENDENCY",
                    "EVIDENCE_BECAME_STALE",
                }
                and decision_name == "REQUEST_HUMAN_REVIEW"
            )
            if depth_limited:
                depth_change = DetectedChange(
                    "AUTONOMOUS_DEPTH_LIMIT_REACHED", f"depth-limit:{change.change_key}",
                    entity_id=change.entity_id, relationship_id=change.relationship_id,
                    before_value={"autonomous_depth": _current_autonomous_depth(investigation)},
                    after_value={"maximum_autonomous_depth": config.max_autonomous_depth},
                    evidence_ids=change.evidence_ids,
                )
                depth_row = _persist_change(db, investigation, run, depth_change, previous_state, before_actions)
                if depth_row is not None:
                    change_rows.append(depth_row)
                    _append_event(investigation, "change_detected", "Autonomous depth limit reached; follow-up was stopped.", change_id=str(depth_row.id))
                decision_name = "REQUEST_HUMAN_REVIEW"
                reason = "The configured autonomous depth limit is reached; further research needs human review."

            change_row = change_rows_by_key.get(change.change_key)
            decision_row = _persist_decision(
                db, investigation, run, change, decision_name, reason, priority,
                change_row=change_row, graph_version=before_actions["graph_version"],
            )
            if decision_row is None:
                continue
            decisions.append(decision_row)
            _append_event(
                investigation,
                "agent_decision",
                f"{decision_name}: {reason}",
                agent_decision_id=str(decision_row.id), trigger_event=change.change_type,
                entity_id=change.entity_id, relationship_id=change.relationship_id,
                priority=priority,
            )

        db.flush()
        db.commit()

        followups_started = 0
        verification_done = False
        risk_done = False
        for decision in decisions:
            if decision.decision == "REQUEST_HUMAN_REVIEW":
                decision.status = "REVIEW_REQUIRED"
                decision.result = "No external action was taken; an analyst should review this event."
                continue
            if decision.decision == "NO_ACTION":
                decision.status = "COMPLETED"
                decision.result = "No autonomous action was needed."
                continue
            if decision.decision == "CREATE_ALERT":
                decision.status = "COMPLETED"
                decision.result = "Existing risk and verification alert rules own alert creation and deduplication."
                continue
            if decision.decision == "REVERIFY_RELATIONSHIP":
                if not verification_done:
                    decision.status = "RUNNING"
                    db.commit()
                    _reverify_and_recalculate(db, investigation)
                    verification_done = True
                    risk_done = True
                decision.status = "COMPLETED"
                decision.result = "The existing verification and risk services reprocessed persisted evidence and graph state."
            elif decision.decision == "RECALCULATE_RISK":
                if not risk_done and investigation.status in {"VERIFICATION_COMPLETED", "RISK_ANALYZED", "COMPLETED"}:
                    decision.status = "RUNNING"
                    db.commit()
                    _recalculate_risk(db, investigation)
                    risk_done = True
                decision.status = "COMPLETED" if risk_done else "SKIPPED"
                decision.result = "Saved risk was recalculated." if risk_done else "Verification must complete before saved risk can be recalculated."
            elif decision.decision in {"RESEARCH_ENTITY", "RESEARCH_RELATIONSHIP"}:
                if followups_started >= MAX_FOLLOWUPS_PER_RUN:
                    decision.status = "SKIPPED"
                    decision.result = f"Per-run safety limit of {MAX_FOLLOWUPS_PER_RUN} follow-up investigations reached."
                    continue
                decision.status = "RUNNING"
                db.commit()
                created = _run_followup_pipeline(db, investigation, config, decision)
                if created is not None and created.status != "FAILED":
                    followups_started += 1
                    decision.status = "COMPLETED"
                    decision.result = "The bounded follow-up completed through the existing planner, research, verification, and risk pipeline."
                elif created is not None:
                    decision.status = "FAILED"
                    decision.result = "The child investigation preserves the follow-up failure state."
                elif decision.status == "RUNNING":
                    decision.status = "SKIPPED"
                    decision.result = decision.result or "Duplicate query or visited-target guard suppressed this follow-up."

        for change in detected:
            alert = create_monitoring_alert(db, investigation, change, run_started_at=run.started_at)
            if alert is not None:
                _append_event(
                    investigation, "alert_created", alert.title,
                    alert_id=str(alert.id), trigger_event=change.change_type,
                )

        current_state = _capture_state(db, investigation, config, as_of=checked_at)
        updated_memory = dict(config.memory_json or {})
        updated_memory.setdefault("decision_keys", [])
        updated_memory["decision_keys"] = sorted(
            set(updated_memory["decision_keys"]) | {row.dedupe_key for row in decisions}
        )
        config.memory_json = _seed_memory(db, investigation, updated_memory)
        snapshot = MonitoringSnapshot(
            investigation_id=investigation.id,
            graph_version=current_state["graph_version"],
            state_json=current_state,
            entity_count=len(current_state["entities"]),
            relationship_count=len(current_state["relationships"]),
            evidence_count=len(current_state["evidence"]),
        )
        db.add(snapshot)
        db.flush()
        run.current_snapshot_id = snapshot.id
        run.status = "MONITORING_COMPLETED"
        run.finished_at = utc_now()
        run.change_count = len(change_rows)
        run.decision_count = len(decisions)
        run.result_json = {
            "graph_version": snapshot.graph_version,
            "change_types": [row.change_type for row in change_rows],
            "decisions": [{"id": str(row.id), "decision": row.decision, "status": row.status} for row in decisions],
            "followups_started": followups_started,
        }
        config.latest_snapshot_id = snapshot.id
        config.last_checked_at = run.finished_at
        config.run_started_at = None
        config.last_error = None
        if config.enabled:
            config.status = "MONITORING_COMPLETED"
            config.next_check_at = run.finished_at + timedelta(minutes=config.interval_minutes)
        else:
            config.status = "MONITORING_DISABLED"
            config.next_check_at = None
        _append_event(
            investigation,
            "monitoring_completed",
            f"Monitoring completed: {len(change_rows)} persisted changes and {len(decisions)} decisions.",
            run_id=str(run.id), graph_version=snapshot.graph_version,
        )
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        logger.exception("Monitoring run %s failed", run_id)
        db.rollback()
        failed_run = db.get(MonitoringRun, run_id)
        failed_config = db.get(MonitoringConfig, run.investigation_id)
        failed_investigation = db.get(Investigation, run.investigation_id)
        now = utc_now()
        if failed_run is not None:
            failed_run.status = "MONITORING_FAILED"
            failed_run.finished_at = now
            failed_run.error_message = "Monitoring failed while reading persisted investigation state."
        if failed_config is not None:
            failed_config.status = "MONITORING_FAILED" if failed_config.enabled else "MONITORING_DISABLED"
            failed_config.last_error = "Monitoring failed. Review server logs before retrying."
            failed_config.last_checked_at = now
            failed_config.run_started_at = None
            failed_config.next_check_at = None
        if failed_investigation is not None:
            _append_event(failed_investigation, "monitoring_failed", "Monitoring failed; no successful completion was recorded.", run_id=str(run_id))
        db.commit()
        return failed_run


def run_due_monitoring_once(*, as_of: datetime | None = None) -> int:
    now = as_of or utc_now()
    started = 0
    with Session(get_engine()) as db:
        due_ids = db.scalars(
            select(MonitoringConfig.investigation_id)
            .where(
                MonitoringConfig.enabled.is_(True),
                MonitoringConfig.status.in_(["MONITORING_ENABLED", "MONITORING_COMPLETED"]),
                MonitoringConfig.next_check_at.is_not(None),
                MonitoringConfig.next_check_at <= now,
            )
            .order_by(MonitoringConfig.next_check_at, MonitoringConfig.investigation_id)
            .limit(50)
        ).all()
    for investigation_id in due_ids:
        with Session(get_engine()) as db:
            investigation = db.get(Investigation, investigation_id)
            if investigation is None:
                continue
            try:
                run = queue_monitoring_run(db, investigation, scheduled=True)
            except (MonitoringDisabledError, MonitoringInProgressError):
                continue
            started += 1
            execute_monitoring_run(db, run.id, as_of=now)
    return started


def monitoring_state(db: Session, investigation_id: UUID) -> dict[str, Any]:
    config = db.get(MonitoringConfig, investigation_id)
    if config is None:
        return {
            "investigation_id": investigation_id,
            "enabled": False,
            "status": "MONITORING_DISABLED",
            "interval_minutes": settings.monitoring_default_interval_minutes,
            "max_autonomous_depth": MAX_AUTONOMOUS_DEPTH,
            "last_checked_at": None,
            "next_check_at": None,
            "last_error": None,
            "graph_version": None,
            "entity_count": 0,
            "relationship_count": 0,
            "evidence_count": 0,
            "last_run": None,
        }
    snapshot = db.get(MonitoringSnapshot, config.latest_snapshot_id) if config.latest_snapshot_id else None
    last_run = db.scalar(
        select(MonitoringRun).where(MonitoringRun.investigation_id == investigation_id)
        .order_by(MonitoringRun.started_at.desc()).limit(1)
    )
    return {
        "investigation_id": investigation_id,
        "enabled": config.enabled,
        "status": config.status,
        "interval_minutes": config.interval_minutes,
        "max_autonomous_depth": config.max_autonomous_depth,
        "last_checked_at": config.last_checked_at,
        "next_check_at": config.next_check_at,
        "last_error": config.last_error,
        "graph_version": None if snapshot is None else snapshot.graph_version,
        "entity_count": 0 if snapshot is None else snapshot.entity_count,
        "relationship_count": 0 if snapshot is None else snapshot.relationship_count,
        "evidence_count": 0 if snapshot is None else snapshot.evidence_count,
        "last_run": None if last_run is None else {
            "id": last_run.id, "status": last_run.status, "started_at": last_run.started_at,
            "finished_at": last_run.finished_at, "change_count": last_run.change_count,
            "decision_count": last_run.decision_count, "result_json": last_run.result_json,
            "error_message": last_run.error_message,
        },
    }


def monitoring_changes(db: Session, investigation_id: UUID, *, limit: int = 100, offset: int = 0) -> tuple[list[InvestigationChange], int]:
    query = select(InvestigationChange).where(InvestigationChange.investigation_id == investigation_id)
    total = db.scalar(select(func.count(InvestigationChange.id)).where(InvestigationChange.investigation_id == investigation_id)) or 0
    rows = db.scalars(query.order_by(InvestigationChange.created_at.desc(), InvestigationChange.id).limit(limit).offset(offset)).all()
    return rows, total


def agent_decisions(db: Session, investigation_id: UUID, *, limit: int = 100, offset: int = 0) -> tuple[list[AgentDecision], int]:
    query = select(AgentDecision).where(AgentDecision.investigation_id == investigation_id)
    total = db.scalar(select(func.count(AgentDecision.id)).where(AgentDecision.investigation_id == investigation_id)) or 0
    rows = db.scalars(query.order_by(AgentDecision.created_at.desc(), AgentDecision.id).limit(limit).offset(offset)).all()
    return rows, total


def _capture_state(db: Session, investigation: Investigation, config: MonitoringConfig, *, as_of: datetime) -> dict[str, Any]:
    entities = db.scalars(select(Entity).where(Entity.investigation_id == investigation.id).order_by(Entity.id)).all()
    relationships = db.scalars(select(Relationship).where(Relationship.investigation_id == investigation.id).order_by(Relationship.id)).all()
    relationship_ids = [row.id for row in relationships]
    evidence_rows = db.scalars(
        select(Evidence).where(or_(
            Evidence.investigation_id == investigation.id,
            and_(Evidence.investigation_id.is_(None), Evidence.relationship_id.in_(relationship_ids)) if relationship_ids else Evidence.id.is_(None),
        )).order_by(Evidence.id)
    ).all()
    entity_by_id = {str(row.id): row for row in entities}
    entity_state = {}
    for row in entities:
        metadata = row.metadata_json or {}
        entity_state[str(row.id)] = {
            "name": row.name,
            "entity_type": row.entity_type,
            "jurisdiction": row.jurisdiction,
            "description_hash": _hash(row.description or ""),
            "identifiers_hash": _hash(row.identifiers or []),
            "metadata_hash": _hash(metadata),
        }
    evidence_by_relationship: dict[str, set[str]] = {}
    evidence_state: dict[str, dict[str, Any]] = {}
    source_keys: set[str] = set()
    evidence_by_id = {str(row.id): row for row in evidence_rows}
    for row in evidence_rows:
        content_hash = _hash(row.content or row.excerpt or "")
        relationship_id = str(row.relationship_id) if row.relationship_id else None
        evidence_state[str(row.id)] = {
            "relationship_id": relationship_id,
            "source": row.source,
            "source_url": row.source_url,
            "content_hash": content_hash,
            "metadata_hash": _hash(row.metadata_json or {}),
            "confidence": row.confidence,
            "published_date": None if row.published_date is None else row.published_date.isoformat(),
            "captured_at": _datetime_text(row.captured_at),
            "verification_status": row.verification_status,
        }
        if relationship_id:
            evidence_by_relationship.setdefault(relationship_id, set()).add(str(row.id))
        source_keys.add(_source_key(row))

    relationship_state: dict[str, dict[str, Any]] = {}
    supporting_evidence_ids: set[str] = set()
    for row in relationships:
        metadata = row.metadata_json or {}
        verification = metadata.get("verification") or {}
        rel_evidence = evidence_by_relationship.get(str(row.id), set())
        rel_evidence |= {str(value) for value in metadata.get("source_evidence_ids", []) if str(value) in evidence_by_id}
        supporting = {str(value) for value in verification.get("supporting_evidence_ids", []) if str(value) in evidence_by_id}
        supporting_evidence_ids.update(supporting)
        relation_record = RelationshipRecord(
            id=str(row.id), source_id=str(row.source_entity_id), target_id=str(row.target_entity_id),
            relationship_type=row.relationship_type, verification_status=row.verification_status,
            confidence=row.confidence, metadata=metadata,
        )
        orientation = dependency_orientation(relation_record)
        consumer_id, provider_id = orientation if orientation else (None, None)
        relationship_state[str(row.id)] = {
            "source_id": str(row.source_entity_id), "target_id": str(row.target_entity_id),
            "relationship_type": row.relationship_type, "verification_status": row.verification_status,
            "confidence": row.confidence, "provider_id": provider_id, "consumer_id": consumer_id,
            "evidence_ids": sorted(rel_evidence),
            "metadata_hash": _hash(metadata),
        }

    stale_cutoff = as_of - timedelta(days=settings.monitoring_evidence_freshness_days)
    stale_ids: set[str] = set()
    for evidence_id in supporting_evidence_ids:
        row = evidence_by_id.get(evidence_id)
        if row is None:
            continue
        evidence_date: datetime | date | None = row.published_date or row.captured_at
        if evidence_date is None:
            continue
        if isinstance(evidence_date, datetime):
            normalized_date = _aware(evidence_date)
            if normalized_date < stale_cutoff:
                stale_ids.add(evidence_id)
        elif datetime.combine(evidence_date, datetime.min.time(), tzinfo=timezone.utc) < stale_cutoff:
            stale_ids.add(evidence_id)

    risk_scores: dict[str, float | None] = {}
    risk_factor_hashes: dict[str, str] = {}
    risk_analysis = investigation.risk_analysis or {}
    snapshot_id = risk_analysis.get("snapshot_id")
    risk_query = select(Risk).where(Risk.investigation_id == investigation.id)
    if snapshot_id:
        try:
            risk_query = risk_query.where(Risk.snapshot_id == UUID(str(snapshot_id)))
        except ValueError:
            risk_query = risk_query.where(Risk.snapshot_id.is_(None))
    else:
        risk_query = risk_query.where(Risk.snapshot_id.is_(None))
    for row in db.scalars(risk_query).all():
        score = row.score
        if score is not None and row.score_scale != "percent":
            score = float(score) * 100.0
        target_id = row.relationship_id or row.entity_id
        risk_scores[str(target_id)] = None if score is None else round(float(score), 2)
        risk_factor_hashes[str(target_id)] = _hash(row.risk_factors or [])

    critical_dependencies = {}
    for item in risk_analysis.get("critical_dependencies", []) if isinstance(risk_analysis, dict) else []:
        if not isinstance(item, dict):
            continue
        related = sorted(str(value) for value in item.get("related_entity_ids", []))
        key = "|".join((str(item.get("type", "")), str(item.get("entity_id", "")), ",".join(related)))
        critical_dependencies[key] = {
            "type": item.get("type"), "entity_id": item.get("entity_id"),
            "related_entity_ids": related, "severity": item.get("severity"),
        }

    owner_id = investigation.owner_id
    watch_scope = [WatchlistEntry.investigation_id == investigation.id]
    if entities:
        watch_scope.append(WatchlistEntry.entity_id.in_([row.id for row in entities]))
    if relationships:
        watch_scope.append(WatchlistEntry.relationship_id.in_([row.id for row in relationships]))
    watch_entries = db.scalars(select(WatchlistEntry).where(
        WatchlistEntry.owner_id == owner_id,
        WatchlistEntry.status == "watching",
        or_(*watch_scope),
    )).all() if owner_id is not None else []
    watchlist_targets = set()
    watchlist_state: dict[str, dict[str, Any]] = {}
    for entry in watch_entries:
        if entry.target_key:
            target_key = str(entry.target_key)
            watchlist_targets.add(target_key)
        elif entry.target_type == "relationship" and entry.relationship_id:
            target_key = f"relationship:{entry.relationship_id}"
            watchlist_targets.add(target_key)
        elif entry.target_type == "investigation" and entry.investigation_id:
            target_key = f"investigation:{entry.investigation_id}"
            watchlist_targets.add(target_key)
        elif entry.entity_id:
            target_key = f"entity:{entry.entity_id}"
            watchlist_targets.add(target_key)
        else:
            continue
        watchlist_state[target_key] = {
            "risk_threshold": entry.risk_threshold,
            "condition": entry.condition_json or {},
            "last_observed": entry.last_observed or {},
        }

    alert_rows = db.scalars(select(Alert).where(
        Alert.investigation_id == investigation.id,
        or_(Alert.owner_id == owner_id, Alert.owner_id.is_(None)),
    )).all()
    alert_state = sorted(
        f"{row.id}:{row.dedupe_key or row.alert_type}:{bool(row.is_read)}:{bool(row.dismissed_at)}"
        for row in alert_rows
    )
    verification_counts: dict[str, int] = {}
    for relation in relationships:
        key = str(relation.verification_status or "UNKNOWN").upper()
        verification_counts[key] = verification_counts.get(key, 0) + 1

    state: dict[str, Any] = {
        "investigation_state": {
            "status": investigation.status,
            "depth": investigation.depth,
            "scope": investigation.scope or {},
            "plan_hash": _hash(investigation.plan or {}),
            "research_mode": investigation.research_mode,
            "verification_mode": investigation.verification_mode,
        },
        "entities": entity_state,
        "relationships": relationship_state,
        "evidence": evidence_state,
        "stale_evidence_ids": sorted(stale_ids),
        "risk_scores": risk_scores,
        "risk_factor_hashes": risk_factor_hashes,
        "critical_dependencies": critical_dependencies,
        "watchlist_targets": sorted(watchlist_targets),
        "watchlist_state": watchlist_state,
        "alert_state": alert_state,
        "verification_state": verification_counts,
        "entity_count": len(entity_state),
        "relationship_count": len(relationship_state),
        "evidence_count": len(evidence_state),
        "source_keys": sorted(source_keys),
    }
    state["graph_version"] = _hash(state)
    return state


def _seed_memory(db: Session, investigation: Investigation, current: dict[str, Any]) -> dict[str, Any]:
    inherited = investigation.autonomous_context or {}
    memory = {
        "visited_entity_ids": set(current.get("visited_entity_ids", [])) | set(inherited.get("visited_entity_ids", [])),
        "visited_relationship_ids": set(current.get("visited_relationship_ids", [])) | set(inherited.get("visited_relationship_ids", [])),
        "executed_query_hashes": set(current.get("executed_query_hashes", [])) | set(inherited.get("executed_query_hashes", [])),
        "processed_source_keys": set(current.get("processed_source_keys", [])) | set(inherited.get("processed_source_keys", [])),
        "resolved_entity_ids": set(current.get("resolved_entity_ids", [])) | set(inherited.get("resolved_entity_ids", [])),
        "verified_relationship_ids": set(current.get("verified_relationship_ids", [])) | set(inherited.get("verified_relationship_ids", [])),
        "decision_keys": set(current.get("decision_keys", [])) | set(inherited.get("decision_keys", [])),
    }
    entities = db.scalars(select(Entity).where(Entity.investigation_id == investigation.id)).all()
    relationships = db.scalars(select(Relationship).where(Relationship.investigation_id == investigation.id)).all()
    memory["visited_entity_ids"].update(str(row.id) for row in entities)
    memory["visited_relationship_ids"].update(str(row.id) for row in relationships)
    memory["resolved_entity_ids"].update(str(row.id) for row in entities if (row.metadata_json or {}).get("canonical_entity_id"))
    memory["verified_relationship_ids"].update(str(row.id) for row in relationships if str(row.verification_status).upper() == "VERIFIED")
    memory["processed_source_keys"].update(current.get("source_keys", []))

    if investigation.plan:
        try:
            plan = InvestigationPlan.model_validate(investigation.plan)
            for query in ResearchAgent().generate_queries(plan):
                memory["executed_query_hashes"].add(_query_key(query.query))
        except Exception:
            logger.info("No reusable plan queries were available for monitoring memory on %s", investigation.id)
    progress_events = (investigation.research_progress or {}).get("events", [])
    for event in progress_events if isinstance(progress_events, list) else []:
        if isinstance(event, dict) and isinstance(event.get("query"), str) and event["query"].strip():
            memory["executed_query_hashes"].add(_query_key(event["query"]))
    return {key: sorted(values) for key, values in memory.items()}


def _persist_change(
    db: Session,
    investigation: Investigation,
    run: MonitoringRun,
    change: DetectedChange,
    previous: dict[str, Any] | None,
    current: dict[str, Any],
) -> InvestigationChange | None:
    fingerprint = _hash({
        "previous": None if previous is None else previous.get("graph_version"),
        "current": current.get("graph_version"), "change": change.as_dict(),
    })
    dedupe_key = f"{change.change_type.lower()}:{fingerprint[:32]}"
    exists = db.scalar(select(InvestigationChange.id).where(
        InvestigationChange.investigation_id == investigation.id,
        InvestigationChange.dedupe_key == dedupe_key,
    ))
    if exists is not None:
        return None
    row = InvestigationChange(
        investigation_id=investigation.id, run_id=run.id, change_type=change.change_type,
        entity_id=_uuid(change.entity_id), relationship_id=_uuid(change.relationship_id),
        before_value=change.before_value, after_value=change.after_value,
        evidence_ids=list(change.evidence_ids), dedupe_key=dedupe_key,
    )
    db.add(row)
    db.flush()
    return row


def _persist_decision(
    db: Session,
    investigation: Investigation,
    run: MonitoringRun,
    change: DetectedChange,
    decision: str,
    reason: str,
    priority: str,
    *,
    change_row: InvestigationChange | None,
    graph_version: str,
) -> AgentDecision | None:
    base = change_row.dedupe_key if change_row is not None else f"{change.change_type}:{change.change_key}:{graph_version}"
    dedupe_key = f"{decision.lower()}:{_hash(base)[:32]}"
    if decision == "NO_ACTION":
        dedupe_key = f"no_action:{run.id}"
    exists = db.scalar(select(AgentDecision.id).where(
        AgentDecision.investigation_id == investigation.id,
        AgentDecision.dedupe_key == dedupe_key,
    ))
    if exists is not None:
        return None
    row = AgentDecision(
        investigation_id=investigation.id, run_id=run.id, trigger_event=change.change_type,
        decision=decision, reason=reason, entity_id=_uuid(change.entity_id),
        relationship_id=_uuid(change.relationship_id), priority=priority,
        evidence_ids=list(change.evidence_ids), status="RECORDED", dedupe_key=dedupe_key,
    )
    db.add(row)
    db.flush()
    return row


def _reverify_and_recalculate(db: Session, investigation: Investigation) -> None:
    db.refresh(investigation)
    if investigation.status not in {"COMPLETED", "RESEARCH_COMPLETED", "VERIFICATION_COMPLETED", "RISK_ANALYZED"}:
        raise MonitoringNotReadyError("Investigation is not in a stable state for re-verification.")
    investigation.status = "COMPLETED"
    investigation.error_message = None
    db.commit()
    start_verification(db, investigation.id)
    execute_verification(db, investigation.id)
    db.refresh(investigation)
    if investigation.status == "VERIFICATION_COMPLETED":
        start_risk_analysis(db, investigation)
        execute_risk_analysis(db, investigation.id)
    db.refresh(investigation)


def _recalculate_risk(db: Session, investigation: Investigation) -> None:
    db.refresh(investigation)
    start_risk_analysis(db, investigation)
    execute_risk_analysis(db, investigation.id)
    db.refresh(investigation)


def _run_followup_pipeline(
    db: Session,
    parent: Investigation,
    config: MonitoringConfig,
    decision: AgentDecision,
) -> Investigation | None:
    target_id = decision.entity_id
    relationship = db.get(Relationship, decision.relationship_id) if decision.relationship_id else None
    if target_id is None and relationship is not None:
        relation_state = _relationship_target(relationship)
        target_id = _uuid(relation_state)
    target = db.get(Entity, target_id) if target_id else None
    if target is None:
        decision.status = "SKIPPED"
        decision.result = "No persisted entity target was available for follow-up research."
        return None

    memory = dict(config.memory_json or {})
    visited = set(memory.get("visited_entity_ids", []))
    if str(target.id) in visited and decision.decision == "RESEARCH_ENTITY":
        decision.status = "SKIPPED"
        decision.result = "This target is already present in investigation memory; duplicate follow-up was suppressed."
        return None
    current_depth = _current_autonomous_depth(parent)
    max_depth = min(MAX_AUTONOMOUS_DEPTH, config.max_autonomous_depth)
    if current_depth >= max_depth:
        decision.status = "REVIEW_REQUIRED"
        decision.result = "Autonomous depth limit reached; no child investigation was created."
        return None

    query_scope = dict(parent.scope or {})
    goal = (
        f"Investigate upstream supply-chain dependencies of {target.name}. "
        f"This is a bounded follow-up because {decision.reason}"
    )
    depth = parent.depth if parent.depth in DEPTH_BY_LABEL else "standard"
    payload = InvestigationCreate(
        name=f"Follow-up: {target.name}"[:240], goal=goal[:10000], depth=depth,
        scope_geography=bool(query_scope.get("geography", True)),
        scope_materials=bool(query_scope.get("materials", True)),
        scope_manufacturers=bool(query_scope.get("manufacturers", True)),
        scope_verification=bool(query_scope.get("verification", True)),
    )
    plan = PlannerAgent().plan(goal=payload.goal, depth=payload.depth, scope=query_scope)
    generated_queries = ResearchAgent().generate_queries(plan)
    known_query_keys = set(memory.get("executed_query_hashes", []))
    fresh_query_indices: list[int] = []
    fresh_query_keys: set[str] = set()
    for index, query in enumerate(generated_queries):
        key = _query_key(query.query)
        if key not in known_query_keys and key not in fresh_query_keys:
            fresh_query_indices.append(index)
            fresh_query_keys.add(key)
    if not fresh_query_keys:
        memory.setdefault("visited_entity_ids", [])
        memory["visited_entity_ids"] = sorted(visited | {str(target.id)})
        config.memory_json = memory
        decision.status = "SKIPPED"
        decision.result = "All proposed research queries match persisted investigation memory; duplicate research was suppressed."
        return None

    child, _ = create_planned_investigation(db, payload, owner_id=parent.owner_id)
    eligible_steps = [
        step for step in plan.steps
        if not re.search(r"\bprepare\b.*\bverification\b", step, flags=re.IGNORECASE)
    ][:max(1, plan.depth * 2 - 1)]
    followup_plan = plan.model_copy(update={
        "steps": [eligible_steps[index] for index in fresh_query_indices],
        "research_questions": [plan.research_questions[min(index, len(plan.research_questions) - 1)] for index in fresh_query_indices],
    })
    child.plan = followup_plan.model_dump(mode="json")
    child.objective = followup_plan.objective
    child.planner_mode = followup_plan.planner_mode
    root_id = (parent.autonomous_context or {}).get("root_investigation_id") or str(parent.id)
    child.autonomous_context = {
        "parent_investigation_id": str(parent.id),
        "root_investigation_id": str(root_id),
        "autonomous_depth": current_depth + 1,
        "maximum_autonomous_depth": max_depth,
        "trigger_event": decision.trigger_event,
        "agent_decision_id": str(decision.id),
        "affected_entity_id": str(target.id),
        "visited_entity_ids": sorted(visited | {str(target.id)}),
        "visited_relationship_ids": sorted(set(memory.get("visited_relationship_ids", [])) | ({str(relationship.id)} if relationship else set())),
        "executed_query_hashes": sorted(set(memory.get("executed_query_hashes", [])) | fresh_query_keys),
        "processed_source_keys": sorted(memory.get("processed_source_keys", [])),
        "resolved_entity_ids": sorted(memory.get("resolved_entity_ids", [])),
        "verified_relationship_ids": sorted(memory.get("verified_relationship_ids", [])),
        "decision_keys": sorted(memory.get("decision_keys", [])),
    }
    db.flush()
    child_memory = {
        "visited_entity_ids": child.autonomous_context["visited_entity_ids"],
        "visited_relationship_ids": child.autonomous_context["visited_relationship_ids"],
        "executed_query_hashes": child.autonomous_context["executed_query_hashes"],
        "processed_source_keys": child.autonomous_context["processed_source_keys"],
        "resolved_entity_ids": child.autonomous_context["resolved_entity_ids"],
        "verified_relationship_ids": child.autonomous_context["verified_relationship_ids"],
        "decision_keys": child.autonomous_context["decision_keys"],
    }
    child_monitor = MonitoringConfig(
        investigation_id=child.id,
        enabled=True,
        status="MONITORING_ENABLED",
        interval_minutes=config.interval_minutes,
        max_autonomous_depth=max_depth,
        enabled_at=utc_now(),
        next_check_at=utc_now() + timedelta(minutes=config.interval_minutes),
        memory_json=child_memory,
    )
    baseline = _capture_state(db, child, child_monitor, as_of=utc_now())
    baseline_snapshot = MonitoringSnapshot(
        investigation_id=child.id,
        graph_version=baseline["graph_version"],
        state_json=baseline,
        entity_count=len(baseline["entities"]),
        relationship_count=len(baseline["relationships"]),
        evidence_count=len(baseline["evidence"]),
    )
    db.add(baseline_snapshot)
    db.flush()
    child_monitor.latest_snapshot_id = baseline_snapshot.id
    db.add(child_monitor)
    decision.followup_investigation_id = child.id
    decision.status = "RUNNING"
    memory["visited_entity_ids"] = sorted(visited | {str(target.id)})
    memory["executed_query_hashes"] = sorted(known_query_keys | fresh_query_keys)
    if relationship is not None:
        memory["visited_relationship_ids"] = sorted(set(memory.get("visited_relationship_ids", [])) | {str(relationship.id)})
    config.memory_json = memory
    _append_event(
        parent, "followup_started", f"Follow-up investigation started for {target.name}.",
        agent_decision_id=str(decision.id), followup_investigation_id=str(child.id), entity_id=str(target.id),
    )
    db.commit()

    try:
        start_research(db, child.id)
        execute_research(db, child.id, build_research_provider(), ResearchAgent())
        db.refresh(child)
        if child.status == "COMPLETED":
            start_verification(db, child.id)
            execute_verification(db, child.id)
            db.refresh(child)
        if child.status == "VERIFICATION_COMPLETED":
            start_risk_analysis(db, child)
            execute_risk_analysis(db, child.id)
            db.refresh(child)
        if child.status == "FAILED":
            decision.status = "FAILED"
            decision.result = "Follow-up pipeline failed; the child investigation preserves the failure state and error summary."
            return child
        _append_event(
            parent, "followup_completed", f"Follow-up investigation {child.name} completed its available pipeline steps.",
            agent_decision_id=str(decision.id), followup_investigation_id=str(child.id),
        )
        decision.followup_investigation_id = child.id
        db.commit()
        return child
    except Exception:
        db.rollback()
        logger.exception("Autonomous follow-up failed for decision %s", decision.id)
        child = db.get(Investigation, child.id)
        decision = db.get(AgentDecision, decision.id)
        if decision is not None:
            decision.status = "FAILED"
            decision.result = "Follow-up pipeline failed; no external action was taken."
        if child is not None:
            _append_event(parent, "followup_completed", f"Follow-up investigation {child.name} failed.", agent_decision_id=str(decision.id) if decision else None)
        db.commit()
        return child


def _relationship_target(relationship: Relationship) -> str | None:
    metadata = relationship.metadata_json or {}
    orientation = dependency_orientation(RelationshipRecord(
        id=str(relationship.id), source_id=str(relationship.source_entity_id),
        target_id=str(relationship.target_entity_id), relationship_type=relationship.relationship_type,
        verification_status=relationship.verification_status, confidence=relationship.confidence, metadata=metadata,
    ))
    return None if orientation is None else orientation[1]


def _source_key(evidence: Evidence) -> str:
    source = (evidence.source_url or f"{evidence.source}:{evidence.title}").strip().lower()
    return _hash(source)


def _query_key(query: str) -> str:
    normalized = re.sub(r"\s+", " ", query.casefold()).strip()
    return _hash(normalized)


def _hash(value: Any) -> str:
    payload = value if isinstance(value, str) else json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _watched_ids(state: dict[str, Any]) -> set[str]:
    return {str(value).split(":", 1)[1] for value in state.get("watchlist_targets", []) if ":" in str(value)}


def _max_depth(investigation: Investigation) -> int:
    context = investigation.autonomous_context or {}
    inherited = context.get("maximum_autonomous_depth")
    if isinstance(inherited, int):
        return max(1, min(MAX_AUTONOMOUS_DEPTH, inherited))
    return max(1, min(MAX_AUTONOMOUS_DEPTH, DEPTH_BY_LABEL.get(investigation.depth, 1)))


def _current_autonomous_depth(investigation: Investigation) -> int:
    context = investigation.autonomous_context or {}
    depth = context.get("autonomous_depth", 0)
    return max(0, int(depth)) if isinstance(depth, (int, float)) else 0


def _append_event(investigation: Investigation, event_type: str, message: str, **details: Any) -> None:
    events = list(investigation.lifecycle_events or [])
    event = {"id": str(uuid4()), "at": utc_now().isoformat(), "type": event_type, "message": message}
    event.update({key: value for key, value in details.items() if value is not None})
    events.append(event)
    investigation.lifecycle_events = events[-200:]


def _uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (ValueError, TypeError):
        return None


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _datetime_text(value: datetime | None) -> str | None:
    return None if value is None else _aware(value).isoformat()
