from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Entity, WatchlistEntry
from app.schemas.watchlist import WatchlistCreate, WatchlistList, WatchlistRead

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _entry_read(entry: WatchlistEntry, entity: Entity) -> WatchlistRead:
    return WatchlistRead(
        id=entry.id,
        entity_id=entry.entity_id,
        status=entry.status,
        created_at=entry.created_at,
        entity_name=entity.name,
        entity_type=entity.entity_type,
        risk_score=entity.risk_score,
        risk_level=entity.risk_level,
    )


@router.get("", response_model=WatchlistList)
def list_watchlist(
    q: str | None = Query(default=None, max_length=160),
    db: Session = Depends(get_db),
) -> WatchlistList:
    statement = select(WatchlistEntry, Entity).join(Entity, Entity.id == WatchlistEntry.entity_id)
    count_statement = select(func.count(WatchlistEntry.id)).join(
        Entity, Entity.id == WatchlistEntry.entity_id
    )
    if q:
        condition = func.lower(Entity.name).like(f"%{q.strip().lower()}%")
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    rows = db.execute(statement.order_by(WatchlistEntry.created_at.desc())).all()
    return WatchlistList(
        items=[_entry_read(entry, entity) for entry, entity in rows],
        total=db.scalar(count_statement) or 0,
    )


@router.post("", response_model=WatchlistRead, status_code=201)
def add_to_watchlist(payload: WatchlistCreate, db: Session = Depends(get_db)) -> WatchlistRead:
    entity = db.get(Entity, payload.entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    entry = WatchlistEntry(entity_id=entity.id)
    db.add(entry)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Entity is already on the watchlist") from exc
    db.refresh(entry)
    return _entry_read(entry, entity)


@router.delete("/{entity_id}", status_code=204)
def remove_from_watchlist(entity_id: UUID, db: Session = Depends(get_db)) -> None:
    entry = db.scalar(select(WatchlistEntry).where(WatchlistEntry.entity_id == entity_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    db.delete(entry)
    db.commit()
