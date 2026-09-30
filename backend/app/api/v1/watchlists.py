from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.entity import Entity
from app.models.user import User
from app.models.watchlist import Watchlist

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


@router.get("", summary="List the current user's watched entities")
def list_watchlist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(Watchlist).where(Watchlist.user_id == user.id).order_by(Watchlist.created_at.desc())))


@router.post("/{entity_id}", status_code=status.HTTP_201_CREATED, summary="Add an entity to the watchlist")
def add_watchlist_item(entity_id: UUID, name: str | None = Query(None, max_length=255), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.get(Entity, entity_id) is None:
        raise HTTPException(404, "Entity not found")
    item = db.scalar(select(Watchlist).where(Watchlist.user_id == user.id, Watchlist.entity_id == entity_id))
    if item is None:
        item = Watchlist(user_id=user.id, entity_id=entity_id, name=name)
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


@router.delete("/{entity_id}", status_code=204, summary="Remove an entity from the watchlist")
def remove_watchlist_item(entity_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.scalar(select(Watchlist).where(Watchlist.user_id == user.id, Watchlist.entity_id == entity_id))
    if item is None:
        raise HTTPException(404, "Watchlist item not found")
    db.delete(item)
    db.commit()
