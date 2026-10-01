import logging
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.access import get_accessible_investigation, owned_investigation_ids
from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import Investigation, Report
from app.models.user import User
from app.schemas.report import ReportCreate, ReportList, ReportRead
from app.services.export_service import export_report
from app.services.report_service import generate_investigation_report

router = APIRouter(prefix="/reports", tags=["reports"])
logger = logging.getLogger(__name__)


@router.get("", response_model=ReportList)
def list_reports(
    investigation_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportList:
    statement = select(Report)
    count_statement = select(func.count(Report.id))
    if investigation_id is not None:
        get_accessible_investigation(db, investigation_id, current_user)
        condition = Report.investigation_id == investigation_id
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    elif not current_user.is_admin:
        owned = Report.investigation_id.in_(owned_investigation_ids(current_user))
        statement = statement.where(owned)
        count_statement = count_statement.where(owned)
    items = db.scalars(statement.order_by(Report.created_at.desc(), Report.id).limit(limit).offset(offset)).all()
    return ReportList(items=items, total=db.scalar(count_statement) or 0)


@router.post("", response_model=ReportRead, status_code=201)
def generate_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    investigation = get_accessible_investigation(db, payload.investigation_id, current_user)
    try:
        return generate_investigation_report(db, investigation)
    except Exception as exc:
        logger.exception("Report generation failed for investigation %s", payload.investigation_id)
        db.rollback()
        failed = db.get(Investigation, payload.investigation_id)
        if failed is not None:
            events = list(failed.lifecycle_events or [])
            events.append({
                "id": str(uuid4()),
                "at": datetime.now(timezone.utc).isoformat(),
                "type": "report_generation_failed",
                "message": "Report generation failed; existing investigation data was preserved.",
            })
            failed.lifecycle_events = events[-200:]
            db.commit()
        raise HTTPException(status_code=500, detail="Report generation failed") from exc


@router.get("/{report_id}", response_model=ReportRead)
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    report = _accessible_report(db, report_id, current_user)
    return report


@router.get("/{report_id}/download")
def download_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    report = _accessible_report(db, report_id, current_user)
    payload = export_report(report, "txt")
    return Response(payload.content, media_type=payload.media_type, headers={
        "Content-Disposition": f'attachment; filename="{payload.filename}"',
    })


@router.get("/{report_id}/export")
def export_report_endpoint(
    report_id: UUID,
    export_format: Literal["json", "csv", "txt"] = Query(alias="format", default="json"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    report = _accessible_report(db, report_id, current_user)
    payload = export_report(report, export_format)
    return Response(payload.content, media_type=payload.media_type, headers={
        "Content-Disposition": f'attachment; filename="{payload.filename}"',
    })


def _accessible_report(db: Session, report_id: UUID, current_user: User) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    get_accessible_investigation(db, report.investigation_id, current_user)
    return report
