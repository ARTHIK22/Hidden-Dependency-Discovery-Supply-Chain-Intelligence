from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.access import owned_investigation_ids
from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import Alert, AlertReceipt, Entity, Investigation, Relationship
from app.models.user import User
from app.schemas.alert import AlertList, AlertRead

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertList)
def list_alerts(
    unread_only: bool = False,
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertList:
    statement = _alert_query(db, current_user)
    if unread_only:
        statement = statement.where(_unread_clause())
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    rows = db.execute(statement.order_by(Alert.created_at.desc(), Alert.id).limit(limit).offset(offset)).all()
    return AlertList(items=[_alert_read(row, current_user) for row in rows], total=db.scalar(count_statement) or 0)


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    statement = select(func.count()).select_from(_alert_query(db, current_user).where(_unread_clause()).order_by(None).subquery())
    return {"unread_count": int(db.scalar(statement) or 0)}


@router.patch("/read-all", status_code=204)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    rows = db.execute(_alert_query(db, current_user).where(_unread_clause())).all()
    now = datetime.now(timezone.utc)
    for alert, _, _, _, _ in rows:
        _get_or_create_receipt(db, alert.id, current_user.id, read_at=now)
    db.commit()
    return Response(status_code=204)


@router.patch("/{alert_id}/read", response_model=AlertRead)
def mark_alert_read(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertRead:
    row = _get_visible_alert(db, alert_id, current_user)
    now = datetime.now(timezone.utc)
    receipt = _get_or_create_receipt(db, alert_id, current_user.id, read_at=now)
    if receipt.read_at is None:
        receipt.read_at = now
    db.commit()
    db.refresh(receipt)
    return _alert_read((*row[:3], receipt, row[4]), current_user)


@router.patch("/{alert_id}/dismiss", status_code=204)
@router.delete("/{alert_id}", status_code=204)
def dismiss_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _get_visible_alert(db, alert_id, current_user)
    receipt = _get_or_create_receipt(db, alert_id, current_user.id, dismissed_at=datetime.now(timezone.utc))
    if receipt.dismissed_at is None:
        receipt.dismissed_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=204)


def _alert_query(db: Session, user: User):
    statement = (
        select(Alert, Entity.name, Relationship, AlertReceipt, Investigation)
        .outerjoin(Entity, Entity.id == Alert.entity_id)
        .outerjoin(Relationship, Relationship.id == Alert.relationship_id)
        .outerjoin(AlertReceipt, and_(AlertReceipt.alert_id == Alert.id, AlertReceipt.user_id == user.id))
        .outerjoin(Investigation, Investigation.id == Alert.investigation_id)
    )
    if not user.is_admin:
        personal = and_(
            Alert.owner_id == user.id,
            Alert.investigation_id.in_(owned_investigation_ids(user)),
        )
        shared_demo = and_(
            Alert.owner_id.is_(None),
            Alert.investigation_id.in_(select(Investigation.id).where(Investigation.demo_mode.is_(True))),
        )
        statement = statement.where(or_(personal, shared_demo))
    demo = func.coalesce(Investigation.demo_mode, False).is_(True)
    visible_dismissal = or_(
        and_(demo, AlertReceipt.dismissed_at.is_not(None)),
        and_(~demo, or_(AlertReceipt.dismissed_at.is_not(None), Alert.dismissed_at.is_not(None))),
    )
    return statement.where(~visible_dismissal)


def _unread_clause():
    demo = func.coalesce(Investigation.demo_mode, False).is_(True)
    demo_unread = and_(demo, AlertReceipt.read_at.is_(None))
    normal_unread = and_(
        ~demo,
        AlertReceipt.read_at.is_(None),
        Alert.read_at.is_(None),
        Alert.is_read.is_(False),
    )
    return or_(demo_unread, normal_unread)


def _get_visible_alert(db: Session, alert_id: UUID, user: User):
    row = db.execute(_alert_query(db, user).where(Alert.id == alert_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return row


def _get_or_create_receipt(
    db: Session,
    alert_id: UUID,
    user_id: UUID,
    *,
    read_at: datetime | None = None,
    dismissed_at: datetime | None = None,
) -> AlertReceipt:
    receipt = db.scalar(select(AlertReceipt).where(AlertReceipt.alert_id == alert_id, AlertReceipt.user_id == user_id))
    if receipt is not None:
        if read_at is not None and receipt.read_at is None:
            receipt.read_at = read_at
        if dismissed_at is not None and receipt.dismissed_at is None:
            receipt.dismissed_at = dismissed_at
        return receipt
    receipt = AlertReceipt(alert_id=alert_id, user_id=user_id, read_at=read_at, dismissed_at=dismissed_at)
    try:
        with db.begin_nested():
            db.add(receipt)
            db.flush()
    except IntegrityError:
        receipt = db.scalar(select(AlertReceipt).where(AlertReceipt.alert_id == alert_id, AlertReceipt.user_id == user_id))
        if receipt is None:
            raise
    return receipt


def _alert_read(row, user: User) -> AlertRead:
    alert, entity_name, relation, receipt, investigation = row
    is_demo = investigation is not None and investigation.demo_mode and alert.owner_id is None
    name = entity_name
    if relation is not None:
        name = f"{relation.relationship_type} relationship"
    receipt_read_at = None if receipt is None else receipt.read_at
    receipt_dismissed_at = None if receipt is None else receipt.dismissed_at
    read_at = receipt_read_at if is_demo else (receipt_read_at or alert.read_at)
    dismissed_at = receipt_dismissed_at if is_demo else (receipt_dismissed_at or alert.dismissed_at)
    return AlertRead(
        id=alert.id, investigation_id=alert.investigation_id, entity_id=alert.entity_id,
        relationship_id=alert.relationship_id, entity_name=name,
        title=alert.title, message=alert.message, alert_type=alert.alert_type,
        severity=alert.severity, reason=alert.reason, risk_score=alert.risk_score,
        evidence_ids=alert.evidence_ids or [], risk_snapshot=alert.risk_snapshot,
        demo_only=is_demo, read_at=read_at, dismissed_at=dismissed_at, created_at=alert.created_at,
    )
