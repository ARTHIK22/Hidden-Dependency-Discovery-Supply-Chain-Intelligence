from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.api.access import get_accessible_investigation, owned_investigation_ids
from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import Entity, Investigation, Relationship, Risk
from app.models.user import User
from app.schemas.risk import RiskAnalysisState, RiskList, RiskRead
from app.services.risk_service import (
    RiskAnalysisInProgressError,
    RiskAnalysisNotReadyError,
    risk_state,
    run_risk_analysis_background,
    start_risk_analysis,
)

router = APIRouter(prefix="/risks", tags=["risks"])
investigation_risks_router = APIRouter(prefix="/investigations", tags=["risk intelligence"])
entity_risks_router = APIRouter(prefix="/entities", tags=["risk intelligence"])
relationship_risks_router = APIRouter(prefix="/relationships", tags=["risk intelligence"])


@router.get("", response_model=RiskList)
def list_risks(
    investigation_id: UUID | None = None,
    level: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RiskList:
    if investigation_id is not None:
        investigation = get_accessible_investigation(db, investigation_id, current_user)
        query = _visible_snapshot_query(db, investigation)
    else:
        investigation_rows = select(Investigation)
        if not current_user.is_admin:
            investigation_rows = investigation_rows.where(Investigation.id.in_(owned_investigation_ids(current_user)))
        investigations = db.scalars(investigation_rows).all()
        clauses = []
        for investigation in investigations:
            clauses.extend(_snapshot_clauses(investigation))
        if current_user.is_admin:
            clauses.append(Risk.investigation_id.is_(None))
        if not clauses:
            return RiskList(items=[], total=0)
        query = _risk_rows_statement().where(or_(*clauses))
    if level:
        query = query.where(func.lower(Risk.level) == level.lower())
    rows = db.execute(query.order_by(Risk.created_at.desc(), Risk.id).limit(limit).offset(offset)).all()
    count_query = select(func.count(Risk.id)).where(query.whereclause)
    return RiskList(items=[_to_read(row) for row in rows], total=db.scalar(count_query) or 0)


@router.get("/summary")
def risk_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int | float]:
    risks = list_risks(level=None, limit=250, offset=0, db=db, current_user=current_user)
    known = [item.score for item in risks.items if item.score is not None]
    return {
        "total": risks.total,
        "high_risk": sum(item.level in {"HIGH", "CRITICAL", "high", "critical"} for item in risks.items),
        "average_score": 0 if not known else round(sum(known) / len(known), 2),
        "unknown": sum(item.score is None for item in risks.items),
    }


@investigation_risks_router.post("/{investigation_id}/analyze-risk", response_model=RiskAnalysisState, status_code=status.HTTP_202_ACCEPTED)
def analyze_investigation_risk(
    investigation_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    investigation = get_accessible_investigation(db, investigation_id, current_user)
    try:
        start_risk_analysis(db, investigation)
    except RiskAnalysisInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RiskAnalysisNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    background_tasks.add_task(run_risk_analysis_background, investigation_id)
    return risk_state(investigation)


@investigation_risks_router.get("/{investigation_id}/risk-analysis", response_model=RiskAnalysisState)
def get_investigation_risk_state(
    investigation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    investigation = get_accessible_investigation(db, investigation_id, current_user)
    return risk_state(investigation)


@investigation_risks_router.get("/{investigation_id}/risks", response_model=RiskList)
def list_investigation_risks(
    investigation_id: UUID,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RiskList:
    investigation = get_accessible_investigation(db, investigation_id, current_user)
    statement = _visible_snapshot_query(db, investigation)
    count = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    rows = db.execute(statement.order_by(Risk.created_at.desc(), Risk.id).limit(limit).offset(offset)).all()
    return RiskList(items=[_to_read(row) for row in rows], total=count)


@investigation_risks_router.get("/{investigation_id}/risk-summary")
def get_investigation_risk_summary(
    investigation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    investigation = get_accessible_investigation(db, investigation_id, current_user)
    analysis = investigation.risk_analysis or {}
    return {
        **dict(analysis.get("summary", {})),
        "investigation_id": str(investigation.id),
        "status": investigation.status,
        "calculated_at": analysis.get("calculated_at"),
        "risk_progress": investigation.risk_progress,
        "unknown_relationship_statuses": (analysis.get("summary") or {}).get("relationship_status_counts", {}),
    }


@entity_risks_router.get("/{entity_id}/risk", response_model=RiskList)
def get_entity_risk(
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RiskList:
    entity = db.get(Entity, entity_id)
    if entity is None or entity.investigation_id is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    investigation = get_accessible_investigation(db, entity.investigation_id, current_user)
    statement = _visible_snapshot_query(db, investigation).where(Risk.entity_id == entity.id, Risk.relationship_id.is_(None))
    rows = db.execute(statement.order_by(Risk.created_at.desc())).all()
    return RiskList(items=[_to_read(row) for row in rows], total=len(rows))


@relationship_risks_router.get("/{relationship_id}/risk", response_model=RiskList)
def get_relationship_risk(
    relationship_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RiskList:
    relation = db.get(Relationship, relationship_id)
    if relation is None or relation.investigation_id is None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    investigation = get_accessible_investigation(db, relation.investigation_id, current_user)
    statement = _visible_snapshot_query(db, investigation).where(Risk.relationship_id == relation.id)
    rows = db.execute(statement.order_by(Risk.created_at.desc())).all()
    return RiskList(items=[_to_read(row) for row in rows], total=len(rows))


def _risk_rows_statement():
    source = aliased(Entity)
    target = aliased(Entity)
    return (
        select(Risk, Entity, Investigation, Relationship, source, target)
        .join(Entity, Entity.id == Risk.entity_id)
        .outerjoin(Investigation, Investigation.id == Risk.investigation_id)
        .outerjoin(Relationship, Relationship.id == Risk.relationship_id)
        .outerjoin(source, source.id == Relationship.source_entity_id)
        .outerjoin(target, target.id == Relationship.target_entity_id)
    )


def _visible_snapshot_query(db: Session, investigation: Investigation):
    statement = _risk_rows_statement().where(Risk.investigation_id == investigation.id)
    snapshot_id = (investigation.risk_analysis or {}).get("snapshot_id")
    if snapshot_id:
        return statement.where(Risk.snapshot_id == UUID(str(snapshot_id)))
    return statement.where(Risk.snapshot_id.is_(None))


def _snapshot_clauses(investigation: Investigation):
    snapshot_id = (investigation.risk_analysis or {}).get("snapshot_id")
    if snapshot_id:
        return [Risk.snapshot_id == UUID(str(snapshot_id))]
    return [Risk.investigation_id == investigation.id, Risk.snapshot_id.is_(None)]


def _to_read(row) -> RiskRead:
    risk, entity, investigation, relation, source, target = row
    score = risk.score
    if score is not None and risk.score_scale != "percent":
        score = float(score) * 100.0
    target_type = "relationship" if risk.relationship_id is not None else "entity"
    name = entity.name if relation is None else f"{source.name if source else 'Unknown'} → {target.name if target else 'Unknown'}"
    entity_type = entity.entity_type if relation is None else relation.relationship_type
    return RiskRead(
        id=risk.id, entity_id=risk.entity_id, entity_name=name, entity_type=entity_type,
        investigation_id=risk.investigation_id, relationship_id=risk.relationship_id,
        snapshot_id=risk.snapshot_id, target_type=target_type,
        score=None if score is None else round(float(score), 2),
        local_score=risk.local_score, propagated_score=risk.propagated_score,
        level=risk.level, reason=risk.reason,
        risk_factors=risk.risk_factors or [],
        demo_mode=bool(investigation.demo_mode) if investigation is not None else False,
        created_at=risk.created_at,
    )
