import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.investigation import Investigation
from app.models.report import Report
from app.models.user import User
from app.services.report_service import build_report

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/investigations/{investigation_id}", summary="Generate a reproducible report from stored investigation data")
def generate_report(investigation_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    investigation = db.get(Investigation, investigation_id)
    if investigation is None or (investigation.created_by != user.id and not user.is_admin):
        raise HTTPException(404, "Investigation not found")
    content = build_report(db, investigation)
    report = Report(investigation_id=investigation.id, title=f"Investigation report: {investigation.name}", report_type="json", content=json.dumps(content, ensure_ascii=False), status="generated")
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"id": str(report.id), **content}
