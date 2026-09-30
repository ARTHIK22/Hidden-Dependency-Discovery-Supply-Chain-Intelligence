from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.models import Alert, Entity, Investigation, Relationship, Risk
from app.schemas.investigation import InvestigationRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)) -> dict[str, object]:
    total_investigations = db.scalar(select(func.count(Investigation.id))) or 0
    active_investigations = db.scalar(
        select(func.count(Investigation.id)).where(
            func.lower(Investigation.status).in_(["queued", "running", "in_progress"])
        )
    ) or 0
    entity_count = db.scalar(select(func.count(Entity.id))) or 0
    relationship_count = db.scalar(select(func.count(Relationship.id))) or 0
    high_risk_count = db.scalar(
        select(func.count(Risk.id)).where(func.lower(Risk.level).in_(["high", "critical"]))
    ) or 0
    unread_alert_count = db.scalar(
        select(func.count(Alert.id)).where(Alert.read_at.is_(None), Alert.dismissed_at.is_(None))
    ) or 0
    recent = db.scalars(
        select(Investigation).order_by(Investigation.created_at.desc()).limit(5)
    ).all()
    return {
        "total_investigations": total_investigations,
        "active_investigations": active_investigations,
        "discovered_entities": entity_count,
        "relationships": relationship_count,
        "high_risk_dependencies": high_risk_count,
        "unread_alerts": unread_alert_count,
        "recent_investigations": [InvestigationRead.model_validate(item).model_dump(mode="json") for item in recent],
    }
