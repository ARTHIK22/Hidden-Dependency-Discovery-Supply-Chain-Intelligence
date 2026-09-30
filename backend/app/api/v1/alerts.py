from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Alert, Entity
from app.schemas.alert import AlertList, AlertRead

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertList)
def list_alerts(
    unread_only: bool = False,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> AlertList:
    statement = select(Alert, Entity.name).outerjoin(Entity, Entity.id == Alert.entity_id)
    count_statement = select(func.count(Alert.id))
    conditions = [Alert.dismissed_at.is_(None)]
    if unread_only:
        conditions.append(Alert.read_at.is_(None))
    for condition in conditions:
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    rows = db.execute(statement.order_by(Alert.created_at.desc()).limit(limit).offset(offset)).all()
    items = [
        AlertRead(
            id=alert.id,
            investigation_id=alert.investigation_id,
            entity_id=alert.entity_id,
            entity_name=entity_name,
            title=alert.title,
            message=alert.message,
            severity=alert.severity,
            read_at=alert.read_at,
            dismissed_at=alert.dismissed_at,
            created_at=alert.created_at,
        )
        for alert, entity_name in rows
    ]
    return AlertList(items=items, total=db.scalar(count_statement) or 0)


@router.patch("/{alert_id}/read", response_model=AlertRead)
def mark_alert_read(alert_id: UUID, db: Session = Depends(get_db)) -> AlertRead:
    alert = db.get(Alert, alert_id)
    if alert is None or alert.dismissed_at is not None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.read_at = alert.read_at or datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    entity = db.get(Entity, alert.entity_id) if alert.entity_id else None
    return AlertRead(
        id=alert.id,
        investigation_id=alert.investigation_id,
        entity_id=alert.entity_id,
        entity_name=entity.name if entity else None,
        title=alert.title,
        message=alert.message,
        severity=alert.severity,
        read_at=alert.read_at,
        dismissed_at=alert.dismissed_at,
        created_at=alert.created_at,
    )


@router.delete("/{alert_id}", status_code=204)
def dismiss_alert(alert_id: UUID, db: Session = Depends(get_db)) -> None:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.dismissed_at = datetime.now(timezone.utc)
    db.commit()
