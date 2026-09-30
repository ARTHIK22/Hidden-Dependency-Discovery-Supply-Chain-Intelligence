from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.entity import Entity
from app.services.graph_service import neighborhood, shortest_path

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get("/{entity_id}", summary="Get the graph neighborhood around an entity")
def get_graph(entity_id: UUID, depth: int = Query(1, ge=1, le=5), db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    if db.get(Entity, entity_id) is None:
        raise HTTPException(404, "Entity not found")
    return neighborhood(db, entity_id, depth)


@router.get("/path/{source_id}/{target_id}", summary="Find a shortest undirected relationship path")
def get_path(source_id: UUID, target_id: UUID, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    path = shortest_path(db, source_id, target_id)
    if path is None:
        raise HTTPException(404, "No relationship path found")
    return {"path": path, "hops": len(path) - 1}
