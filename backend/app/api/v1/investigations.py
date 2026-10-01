from uuid import UUID

import asyncio
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.dependencies import get_current_user, resolve_user
from app.api.access import owned_investigation_ids
from app.core.database import get_db, get_engine
from app.models import Entity, Evidence, Investigation, Relationship, Risk
from app.models.user import User
from app.schemas.entity import EntityList, EntityRead
from app.schemas.research import ResearchState
from app.schemas.relationship import RelationshipRead
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationCreated,
    InvestigationDetail,
    InvestigationList,
    InvestigationPlanResponse,
    InvestigationRead,
)
from app.services.investigation_service import (
    InvestigationPlanningError,
    create_planned_investigation,
)
from app.services.research_service import (
    ResearchNotReadyError,
    research_state,
    run_research_background,
    start_research,
)
from app.schemas.verification import VerificationState
from app.services.verification_service import (
    VerificationNotReadyError,
    run_verification_background,
    start_verification,
    verification_state,
)
from app.schemas.monitoring import (
    AgentDecisionRead,
    InvestigationChangeRead,
    MonitoringEnableRequest,
    MonitoringRunAccepted,
    MonitoringState,
)
from app.services.monitoring_service import (
    MonitoringDisabledError,
    MonitoringInProgressError,
    MonitoringNotReadyError,
    agent_decisions,
    disable_monitoring,
    enable_monitoring,
    monitoring_changes,
    monitoring_state,
    queue_monitoring_run,
    run_monitoring_background,
)

router = APIRouter(prefix="/investigations", tags=["investigations"])
websocket_router = APIRouter(tags=["investigations"])


@router.get("", response_model=InvestigationList)
def list_investigations(
    q: str | None = Query(default=None, max_length=160),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestigationList:
    query = select(Investigation)
    count_query = select(func.count(Investigation.id))
    if not current_user.is_admin:
        owner_filter = Investigation.id.in_(owned_investigation_ids(current_user))
        query = query.where(owner_filter)
        count_query = count_query.where(owner_filter)
    if q:
        term = f"%{q.strip().lower()}%"
        condition = func.lower(Investigation.name).like(term) | func.lower(Investigation.goal).like(term)
        query = query.where(condition)
        count_query = count_query.where(condition)
    items = db.scalars(query.order_by(Investigation.created_at.desc()).limit(limit).offset(offset)).all()
    return InvestigationList(items=items, total=db.scalar(count_query) or 0)


@router.post("", response_model=InvestigationCreated, status_code=201)
def create_investigation(
    payload: InvestigationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        investigation, plan = create_planned_investigation(db, payload, owner_id=current_user.id)
    except InvestigationPlanningError as exc:
        raise HTTPException(status_code=500, detail="Investigation planning failed") from exc
    return {"investigation": investigation, "plan": plan}


@router.get("/{investigation_id}/plan", response_model=InvestigationPlanResponse)
def get_investigation_plan(
    investigation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestigationPlanResponse:
    investigation = _require_investigation(db, investigation_id, current_user)
    if investigation.plan is None:
        raise HTTPException(status_code=404, detail="Investigation plan not found")
    return InvestigationPlanResponse.model_validate(investigation.plan)


@router.get("/{investigation_id}", response_model=InvestigationDetail)
def get_investigation(
    investigation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    investigation = _require_investigation(db, investigation_id, current_user)
    entities_count = db.scalar(
        select(func.count(Entity.id)).where(Entity.investigation_id == investigation_id)
    ) or 0
    relationships_count = db.scalar(
        select(func.count(Relationship.id)).where(Relationship.investigation_id == investigation_id)
    ) or 0
    evidence_count = db.scalar(
        select(func.count(Evidence.id)).where(or_(
            Evidence.investigation_id == investigation_id,
            and_(Evidence.investigation_id.is_(None), Evidence.relationship_id.in_(select(Relationship.id).where(Relationship.investigation_id == investigation_id))),
        ))
    ) or 0
    risk_count = db.scalar(
        select(func.count(Risk.id)).where(Risk.investigation_id == investigation_id)
    ) or 0
    return {
        **InvestigationRead.model_validate(investigation).model_dump(),
        "entities_count": entities_count,
        "relationships_count": relationships_count,
        "evidence_count": evidence_count,
        "risk_count": risk_count,
        "timeline": list(investigation.lifecycle_events or []),
    }


@router.post("/{investigation_id}/monitor", response_model=MonitoringState)
def enable_investigation_monitoring(
    investigation_id: UUID,
    payload: MonitoringEnableRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonitoringState:
    investigation = _require_investigation(db, investigation_id, current_user)
    try:
        enable_monitoring(db, investigation, None if payload is None else payload.interval_minutes)
    except MonitoringNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MonitoringState.model_validate(monitoring_state(db, investigation_id))


@router.delete("/{investigation_id}/monitor", response_model=MonitoringState)
def disable_investigation_monitoring(
    investigation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonitoringState:
    investigation = _require_investigation(db, investigation_id, current_user)
    try:
        disable_monitoring(db, investigation)
    except MonitoringInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MonitoringState.model_validate(monitoring_state(db, investigation_id))


@router.post("/{investigation_id}/monitor/run", response_model=MonitoringRunAccepted, status_code=202)
def run_investigation_monitoring(
    investigation_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonitoringRunAccepted:
    investigation = _require_investigation(db, investigation_id, current_user)
    try:
        run = queue_monitoring_run(db, investigation)
    except MonitoringDisabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MonitoringInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    background_tasks.add_task(run_monitoring_background, run.id)
    return MonitoringRunAccepted(
        investigation_id=investigation_id,
        run_id=run.id,
        status=run.status,
        message="Monitoring run queued.",
    )


@router.get("/{investigation_id}/monitoring", response_model=MonitoringState)
def get_investigation_monitoring(
    investigation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonitoringState:
    _require_investigation(db, investigation_id, current_user)
    return MonitoringState.model_validate(monitoring_state(db, investigation_id))


@router.get("/{investigation_id}/changes")
def list_investigation_changes(
    investigation_id: UUID,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    _require_investigation(db, investigation_id, current_user)
    rows, total = monitoring_changes(db, investigation_id, limit=limit, offset=offset)
    return {"items": [InvestigationChangeRead.model_validate(row) for row in rows], "total": total}


@router.get("/{investigation_id}/agent-decisions")
def list_investigation_agent_decisions(
    investigation_id: UUID,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    _require_investigation(db, investigation_id, current_user)
    rows, total = agent_decisions(db, investigation_id, limit=limit, offset=offset)
    return {"items": [AgentDecisionRead.model_validate(row) for row in rows], "total": total}


@router.post("/{investigation_id}/research", response_model=ResearchState, status_code=202)
def begin_research(
    investigation_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResearchState:
    _require_investigation(db, investigation_id, current_user)
    try:
        investigation, _provider = start_research(db, investigation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc
    except ResearchNotReadyError as exc:
        status_code = 422 if "plan" in str(exc).lower() else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    background_tasks.add_task(run_research_background, investigation_id)
    return ResearchState.model_validate(research_state(investigation))


@router.get("/{investigation_id}/research", response_model=ResearchState)
def get_research_state(
    investigation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResearchState:
    investigation = _require_investigation(db, investigation_id, current_user)
    return ResearchState.model_validate(research_state(investigation))


@router.get("/{investigation_id}/evidence")
def list_investigation_evidence(
    investigation_id: UUID,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    _require_investigation(db, investigation_id, current_user)
    rows = db.scalars(
        select(Evidence)
        .where(or_(
            Evidence.investigation_id == investigation_id,
            and_(Evidence.investigation_id.is_(None), Evidence.relationship_id.in_(select(Relationship.id).where(Relationship.investigation_id == investigation_id))),
        ))
        .order_by(Evidence.captured_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    total = db.scalar(
        select(func.count(Evidence.id)).where(or_(
            Evidence.investigation_id == investigation_id,
            and_(Evidence.investigation_id.is_(None), Evidence.relationship_id.in_(select(Relationship.id).where(Relationship.investigation_id == investigation_id))),
        ))
    ) or 0
    return {
        "items": [
            {
                "id": row.id,
                "investigation_id": row.investigation_id,
                "relationship_id": row.relationship_id,
                "source": row.source,
                "source_type": row.source_type,
                "source_url": row.source_url,
                "title": row.title,
                "excerpt": row.excerpt,
                "captured_at": row.captured_at,
                "verification_status": row.verification_status,
                "metadata": row.metadata_json,
            }
            for row in rows
        ],
        "total": total,
    }


@router.get("/{investigation_id}/entities", response_model=EntityList)
def list_investigation_entities(
    investigation_id: UUID,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EntityList:
    _require_investigation(db, investigation_id, current_user)
    statement = select(Entity).where(Entity.investigation_id == investigation_id)
    entities = db.scalars(statement.order_by(Entity.name).limit(limit).offset(offset)).all()
    total = db.scalar(
        select(func.count(Entity.id)).where(Entity.investigation_id == investigation_id)
    ) or 0
    entity_reads = []
    for row in entities:
        data = EntityRead.model_validate(row).model_dump()
        metadata = row.metadata_json or {}
        resolution = metadata.get("resolution") or {}
        canonical = metadata.get("canonical_entity_id")
        try:
            canonical = UUID(str(canonical)) if canonical else None
        except ValueError:
            canonical = None
        data.update({
            "normalized_name": metadata.get("normalized_name"), "aliases": metadata.get("aliases") or [],
            "canonical_entity_id": canonical,
            "canonical_entity_name": _canonical_entity_name(db, row, canonical),
            "resolution_status": metadata.get("resolution_status") or resolution.get("status"),
            "resolution_confidence": metadata.get("resolution_confidence", resolution.get("confidence")),
            "evidence_count": len(metadata.get("source_evidence_ids") or []),
            "sources": metadata.get("sources") or [],
        })
        if not data["sources"] and metadata.get("source_evidence_ids"):
            evidence_ids = []
            for value in metadata["source_evidence_ids"]:
                try:
                    evidence_ids.append(UUID(str(value)))
                except ValueError:
                    continue
            if evidence_ids:
                data["sources"] = sorted({item.source for item in db.scalars(select(Evidence).where(Evidence.id.in_(evidence_ids))).all()})
        entity_reads.append(EntityRead(**data))
    return EntityList(items=entity_reads, total=total)


def _canonical_entity_name(db: Session, entity: Entity, canonical_id: UUID | None) -> str:
    if canonical_id is None:
        return entity.name
    canonical = db.scalar(select(Entity).where(Entity.id == canonical_id, Entity.investigation_id == entity.investigation_id))
    return canonical.name if canonical is not None else entity.name


@router.get("/{investigation_id}/relationships")
def list_investigation_relationships(
    investigation_id: UUID,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    _require_investigation(db, investigation_id, current_user)
    statement = select(Relationship).where(Relationship.investigation_id == investigation_id)
    rows = db.scalars(statement.order_by(Relationship.created_at).limit(limit).offset(offset)).all()
    total = db.scalar(
        select(func.count(Relationship.id)).where(Relationship.investigation_id == investigation_id)
    ) or 0
    items = []
    for row in rows:
        data = RelationshipRead.model_validate(row).model_dump(mode="json")
        verification = (row.metadata_json or {}).get("verification")
        related_evidence = db.scalars(select(Evidence).where(
            Evidence.relationship_id == row.id,
            or_(Evidence.investigation_id == investigation_id, Evidence.investigation_id.is_(None)),
        )).all()
        data.update({
            "verification": verification,
            "evidence_count": len(verification.get("evidence_ids", [])) if verification else len(related_evidence),
            "sources": sorted({evidence.source for evidence in related_evidence}),
            "conflict_flag": bool(verification and verification.get("conflicting_evidence_ids")),
        })
        items.append(data)
    return {"items": items, "total": total}


@router.post("/{investigation_id}/verify", response_model=VerificationState, status_code=202)
def begin_verification(
    investigation_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VerificationState:
    _require_investigation(db, investigation_id, current_user)
    try:
        investigation = start_verification(db, investigation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc
    except VerificationNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    background_tasks.add_task(run_verification_background, investigation_id)
    return VerificationState.model_validate(verification_state(investigation))


@router.get("/{investigation_id}/verification", response_model=VerificationState)
def get_verification_state(
    investigation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VerificationState:
    investigation = _require_investigation(db, investigation_id, current_user)
    return VerificationState.model_validate(verification_state(investigation))


def _require_investigation(db: Session, investigation_id: UUID, current_user: User) -> Investigation:
    investigation = db.get(Investigation, investigation_id)
    if investigation is None or (
        not current_user.is_admin and investigation.owner_id != current_user.id
        and not (investigation.owner_id is None and investigation.demo_mode)
    ):
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation


@websocket_router.websocket("/ws/investigations/{investigation_id}")
async def investigation_progress(websocket: WebSocket, investigation_id: UUID) -> None:
    monitoring_event_types = {
        "monitoring_started", "change_detected", "agent_decision", "followup_started",
        "followup_completed", "monitoring_completed", "monitoring_failed",
    }
    origin = websocket.headers.get("origin")
    if origin and origin.rstrip("/") not in settings.allowed_origins:
        await websocket.close(code=1008, reason="Origin is not allowed")
        return
    offered_protocols = [part.strip() for part in websocket.headers.get("sec-websocket-protocol", "").split(",")]
    token_protocol = next((part for part in offered_protocols if part.startswith("bearer.")), None)
    if token_protocol is None:
        await websocket.close(code=1008, reason="Authentication required")
        return
    try:
        with Session(get_engine()) as db:
            current_user = resolve_user(token_protocol.removeprefix("bearer."), db)
            row = db.get(Investigation, investigation_id)
            if row is not None and not current_user.is_admin and row.owner_id != current_user.id and not (row.owner_id is None and row.demo_mode):
                row = None
            seen_lifecycle_event_ids = {
                str(event.get("id")) for event in (row.lifecycle_events or [])
                if row is not None and isinstance(event, dict) and event.get("id")
            } if row is not None else set()
        if row is None:
            await websocket.accept(subprotocol="hdi")
            await websocket.send_json({"type": "error", "message": "Investigation not found"})
            await websocket.close(code=1008)
            return
        await websocket.accept(subprotocol="hdi")
        last_updated: datetime | None = None
        while True:
            with Session(get_engine()) as db:
                current = db.get(Investigation, investigation_id)
                if current is None:
                    await websocket.send_json({"type": "error", "message": "Investigation not found"})
                    await websocket.close(code=1008)
                    return
                owned = current.owner_id == current_user.id or current_user.is_admin or (current.owner_id is None and current.demo_mode)
                if not owned:
                    await websocket.close(code=1008, reason="Investigation not found")
                    return
                updated_at = current.updated_at
                if last_updated is None or updated_at != last_updated:
                    serialized = InvestigationRead.model_validate(current).model_dump(mode="json")
                    if current.status in {"VERIFYING", "VERIFICATION_COMPLETED"}:
                        progress = current.verification_progress or {}
                        event_type = "verification_progress"
                    elif current.status in {"RISK_ANALYZING", "RISK_ANALYZED"}:
                        progress = current.risk_progress or {}
                        event_type = "risk_progress"
                    else:
                        progress = current.research_progress or {}
                        event_type = "research_progress" if current.research_mode else "snapshot"
                    await websocket.send_json(
                        {
                            "type": event_type,
                            "investigation": serialized,
                            "investigation_id": str(current.id),
                            "status": current.status,
                            "research_mode": current.research_mode,
                            "progress": progress,
                            "verification_mode": current.verification_mode,
                            "verification": current.verification_progress,
                            "risk_progress": current.risk_progress,
                            "risk_analysis": current.risk_analysis,
                            "lifecycle_events": current.lifecycle_events or [],
                            "message": progress.get("message") or (
                                "DEMO ONLY: deterministic fixture data; no external research occurred."
                                if current.demo_mode
                                else "Current persisted investigation status."
                            ),
                        }
                    )
                    last_updated = updated_at
                for lifecycle_event in current.lifecycle_events or []:
                    if not isinstance(lifecycle_event, dict):
                        continue
                    event_id = str(lifecycle_event.get("id") or "")
                    event_type = str(lifecycle_event.get("type") or "")
                    if event_id and event_id not in seen_lifecycle_event_ids and event_type in monitoring_event_types:
                        await websocket.send_json({
                            "type": event_type,
                            "investigation_id": str(current.id),
                            "event": lifecycle_event,
                        })
                        seen_lifecycle_event_ids.add(event_id)
            terminal = current.status in {"COMPLETED", "FAILED", "completed", "failed"}
            if terminal:
                await websocket.close(code=1000)
                return
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.75)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        return
    except HTTPException:
        await websocket.close(code=1008, reason="Authentication required")
    except Exception:
        try:
            if not websocket.client_state.name == "CONNECTED":
                await websocket.accept(subprotocol="hdi")
            await websocket.send_json(
                {"type": "error", "message": "Investigation progress is unavailable"}
            )
            await websocket.close(code=1013)
        except RuntimeError:
            return
