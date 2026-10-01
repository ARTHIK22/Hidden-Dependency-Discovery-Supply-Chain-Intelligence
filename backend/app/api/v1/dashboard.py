from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.access import owned_investigation_ids
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import Alert, AlertReceipt, Entity, Investigation, Relationship, Risk, WatchlistEntry
from app.models.user import User
from app.schemas.investigation import InvestigationRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    owned_ids = owned_investigation_ids(current_user)
    investigation_scope = select(Investigation.id) if current_user.is_admin else owned_ids
    total_investigations = db.scalar(select(func.count(Investigation.id)).where(Investigation.id.in_(investigation_scope))) or 0
    completed_investigations = db.scalar(
        select(func.count(Investigation.id)).where(
            Investigation.id.in_(investigation_scope), func.lower(Investigation.status).in_(["completed", "risk_analyzed"])
        )
    ) or 0
    active_investigations = db.scalar(
        select(func.count(Investigation.id)).where(
            Investigation.id.in_(investigation_scope),
            func.lower(Investigation.status).not_in(["completed", "failed", "archived"]),
        )
    ) or 0
    entity_count = db.scalar(select(func.count(Entity.id)).where(Entity.investigation_id.in_(investigation_scope))) or 0
    relationship_count = db.scalar(select(func.count(Relationship.id)).where(Relationship.investigation_id.in_(investigation_scope))) or 0
    investigations = db.scalars(
        select(Investigation).where(Investigation.id.in_(investigation_scope))
    ).all()
    latest_snapshot_ids = [
        UUID(str((row.risk_analysis or {}).get("snapshot_id")))
        for row in investigations
        if _is_uuid((row.risk_analysis or {}).get("snapshot_id"))
    ]
    risk_query = select(func.count(Risk.id)).where(
        Risk.investigation_id.in_(investigation_scope),
        Risk.snapshot_id.is_not(None),
        func.upper(Risk.level).in_(["HIGH", "CRITICAL"]),
    )
    high_risk_count = (db.scalar(risk_query.where(Risk.snapshot_id.in_(latest_snapshot_ids))) or 0) if latest_snapshot_ids else 0

    receipt = AlertReceipt
    alert_statement = select(func.count(Alert.id)).outerjoin(
        receipt, and_(receipt.alert_id == Alert.id, receipt.user_id == current_user.id)
    ).outerjoin(Investigation, Investigation.id == Alert.investigation_id)
    demo = func.coalesce(Investigation.demo_mode, False).is_(True)
    if not current_user.is_admin:
        alert_statement = alert_statement.where(or_(
            and_(Alert.owner_id == current_user.id, Alert.investigation_id.in_(owned_ids)),
            and_(Alert.owner_id.is_(None), Alert.investigation_id.in_(select(Investigation.id).where(Investigation.demo_mode.is_(True)))),
        ))
    unread = or_(
        and_(demo, receipt.read_at.is_(None), receipt.dismissed_at.is_(None)),
        and_(~demo, receipt.read_at.is_(None), Alert.read_at.is_(None), Alert.is_read.is_(False), Alert.dismissed_at.is_(None), receipt.dismissed_at.is_(None)),
    )
    unread_alert_count = db.scalar(alert_statement.where(unread)) or 0
    demo_entities = select(Entity.id).join(Investigation, Investigation.id == Entity.investigation_id).where(Investigation.demo_mode.is_(True))
    demo_relationships = select(Relationship.id).join(Investigation, Investigation.id == Relationship.investigation_id).where(Investigation.demo_mode.is_(True))
    demo_investigations = select(Investigation.id).where(Investigation.demo_mode.is_(True))
    watchlist_query = select(func.count(WatchlistEntry.id))
    if not current_user.is_admin:
        watchlist_query = watchlist_query.where(or_(
            WatchlistEntry.owner_id == current_user.id,
            and_(
                WatchlistEntry.owner_id.is_(None),
                or_(WatchlistEntry.entity_id.in_(demo_entities), WatchlistEntry.relationship_id.in_(demo_relationships), WatchlistEntry.investigation_id.in_(demo_investigations)),
            ),
        ))
    watchlist_count = db.scalar(watchlist_query) or 0

    recent = db.scalars(
        select(Investigation)
        .where(Investigation.id.in_(investigation_scope))
        .order_by(Investigation.created_at.desc())
        .limit(5)
    ).all()
    return {
        "total_investigations": total_investigations,
        "active_investigations": active_investigations,
        "completed_investigations": completed_investigations,
        "discovered_entities": entity_count,
        "relationships": relationship_count,
        "high_risk_dependencies": high_risk_count,
        "unread_alerts": int(unread_alert_count),
        "watchlist_items": watchlist_count,
        "demo_mode": settings.development_demo_mode,
        "recent_investigations": [InvestigationRead.model_validate(item).model_dump(mode="json") for item in recent],
    }


def _is_uuid(value: object) -> bool:
    if not value:
        return False
    try:
        UUID(str(value))
        return True
    except (TypeError, ValueError, AttributeError):
        return False
