from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.alert import Alert
from app.models.investigation import Investigation
from app.models.user import User

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", summary="List alerts")
def list_alerts(unread: bool = False, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Alert).outerjoin(Investigation, Alert.investigation_id == Investigation.id).where(
        or_(Investigation.created_by == user.id, user.is_admin)
    ).order_by(Alert.created_at.desc()).limit(limit)
    if unread:
        stmt = stmt.where(Alert.is_read.is_(False))
    return list(db.scalars(stmt))


@router.post("/{alert_id}/read", summary="Mark an alert as read")
def mark_read(alert_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    alert = db.scalar(select(Alert).outerjoin(
        Investigation, Alert.investigation_id == Investigation.id
    ).where(
        Alert.id == alert_id,
        or_(Investigation.created_by == user.id, user.is_admin),
    ))
    if alert is None:
        raise HTTPException(404, "Alert not found")
    alert.is_read = True
    db.commit()
    return alert
