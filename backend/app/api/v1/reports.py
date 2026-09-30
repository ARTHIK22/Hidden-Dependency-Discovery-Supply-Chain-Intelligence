from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Entity, Investigation, Relationship, Report, Risk
from app.schemas.report import ReportCreate, ReportList, ReportRead

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=ReportList)
def list_reports(
    investigation_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ReportList:
    statement = select(Report)
    count_statement = select(func.count(Report.id))
    if investigation_id:
        statement = statement.where(Report.investigation_id == investigation_id)
        count_statement = count_statement.where(Report.investigation_id == investigation_id)
    items = db.scalars(statement.order_by(Report.created_at.desc()).limit(limit).offset(offset)).all()
    return ReportList(items=items, total=db.scalar(count_statement) or 0)


@router.post("", response_model=ReportRead, status_code=201)
def generate_report(payload: ReportCreate, db: Session = Depends(get_db)) -> Report:
    investigation = db.get(Investigation, payload.investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    entity_count = db.scalar(
        select(func.count(Entity.id)).where(Entity.investigation_id == investigation.id)
    ) or 0
    relationship_count = db.scalar(
        select(func.count(Relationship.id)).where(Relationship.investigation_id == investigation.id)
    ) or 0
    risk_rows = db.execute(
        select(Entity.name, Risk.score, Risk.level, Risk.reason)
        .join(Risk, Risk.entity_id == Entity.id)
        .where(Risk.investigation_id == investigation.id)
        .order_by(Risk.score.desc())
    ).all()
    lines = [
        "HIDDEN DEPENDENCY DISCOVERY",
        "INVESTIGATION REPORT",
        "",
        "Investigation: " + investigation.name,
        "Investigation ID: " + str(investigation.id),
        "Status: " + investigation.status,
        "Entities: " + str(entity_count),
        "Relationships: " + str(relationship_count),
        "Risk records: " + str(len(risk_rows)),
        "",
        "Risk records are derived from persisted backend data. This report does not synthesize findings.",
    ]
    for name, score, level, reason in risk_rows:
        lines.extend(["", f"{name}: {score:g} ({level})", reason])
    report = Report(
        investigation_id=investigation.id,
        title=investigation.name + " — Investigation Report",
        content="\n".join(lines),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/{report_id}", response_model=ReportRead)
def get_report(report_id: UUID, db: Session = Depends(get_db)) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/download", response_class=PlainTextResponse)
def download_report(report_id: UUID, db: Session = Depends(get_db)) -> PlainTextResponse:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return PlainTextResponse(
        report.content,
        headers={"Content-Disposition": f'attachment; filename="report-{report.id}.txt"'},
    )
