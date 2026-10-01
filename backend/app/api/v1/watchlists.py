from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.watchlist import WatchlistCreate, WatchlistList, WatchlistRead
from app.services.watchlist_service import (
    add_watchlist_entry,
    list_watchlist,
    remove_entity_watch,
    remove_watchlist_entry,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=WatchlistList)
def get_watchlist(
    q: str | None = Query(default=None, max_length=160),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WatchlistList:
    return list_watchlist(db, current_user, q)


@router.post("", response_model=WatchlistRead, status_code=201)
def add_to_watchlist(
    payload: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WatchlistRead:
    return add_watchlist_entry(db, payload, current_user)


@router.delete("/items/{entry_id}", status_code=204)
def remove_watchlist_item(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    remove_watchlist_entry(db, entry_id, current_user)
    return Response(status_code=204)


@router.delete("/{entity_id}", status_code=204)
def remove_from_watchlist(
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    remove_entity_watch(db, entity_id, current_user)
    return Response(status_code=204)
