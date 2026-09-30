from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Entity, Risk
from app.schemas.risk import RiskList, RiskRead

router = APIRouter(prefix="/risks", tags=["risks"])


@router.get("", response_model=RiskList)
def list_risks(
    investigation_id: UUID | None = None,
    level: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> RiskList:
    statement = select(Risk, Entity).join(Entity, Entity.id == Risk.entity_id)
    count_statement = select(func.count(Risk.id))
    if investigation_id:
        statement = statement.where(Risk.investigation_id == investigation_id)
        count_statement = count_statement.where(Risk.investigation_id == investigation_id)
    if level:
        statement = statement.where(func.lower(Risk.level) == level.lower())
        count_statement = count_statement.where(func.lower(Risk.level) == level.lower())
    rows = db.execute(statement.order_by(Risk.created_at.desc()).limit(limit).offset(offset)).all()
    items = [
        RiskRead(
            id=risk.id,
            entity_id=risk.entity_id,
            entity_name=entity.name,
            entity_type=entity.entity_type,
            investigation_id=risk.investigation_id,
            score=risk.score,
            level=risk.level,
            reason=risk.reason,
            created_at=risk.created_at,
        )
        for risk, entity in rows
    ]
    return RiskList(items=items, total=db.scalar(count_statement) or 0)


@router.get("/summary")
def risk_summary(db: Session = Depends(get_db)) -> dict[str, int | float]:
    total = db.scalar(select(func.count(Risk.id))) or 0
    high = db.scalar(
        select(func.count(Risk.id)).where(func.lower(Risk.level).in_(["high", "critical"]))
    ) or 0
    average = db.scalar(select(func.avg(Risk.score))) or 0
    return {"total": total, "high_risk": high, "average_score": round(float(average), 2)}
