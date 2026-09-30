from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, get_engine
from app.models import Entity, Investigation, Relationship, Risk
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationCreated,
    InvestigationDetail,
    InvestigationList,
    InvestigationRead,
)

router = APIRouter(prefix="/investigations", tags=["investigations"])
websocket_router = APIRouter(tags=["investigations"])


@router.get("", response_model=InvestigationList)
def list_investigations(
    q: str | None = Query(default=None, max_length=160),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> InvestigationList:
    query = select(Investigation)
    count_query = select(func.count(Investigation.id))
    if q:
        term = f"%{q.strip().lower()}%"
        condition = func.lower(Investigation.name).like(term) | func.lower(Investigation.goal).like(term)
        query = query.where(condition)
        count_query = count_query.where(condition)
    items = db.scalars(query.order_by(Investigation.created_at.desc()).limit(limit).offset(offset)).all()
    return InvestigationList(items=items, total=db.scalar(count_query) or 0)


@router.post("", response_model=InvestigationCreated, status_code=201)
def create_investigation(
    payload: InvestigationCreate,
    db: Session = Depends(get_db),
) -> dict[str, Investigation]:
    scope = {
        "geography": payload.scope_geography,
        "materials": payload.scope_materials,
        "manufacturers": payload.scope_manufacturers,
        "verification": payload.scope_verification,
    }
    investigation = Investigation(
        name=(payload.name or payload.goal.strip()[:240]),
        goal=payload.goal.strip(),
        scope=scope,
        depth=payload.depth,
        status="queued",
        progress=0,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    return {"investigation": investigation}


@router.get("/{investigation_id}", response_model=InvestigationDetail)
def get_investigation(
    investigation_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    entities_count = db.scalar(
        select(func.count(Entity.id)).where(Entity.investigation_id == investigation_id)
    ) or 0
    relationships_count = db.scalar(
        select(func.count(Relationship.id)).where(Relationship.investigation_id == investigation_id)
    ) or 0
    risk_count = db.scalar(
        select(func.count(Risk.id)).where(Risk.investigation_id == investigation_id)
    ) or 0
    return {
        **InvestigationRead.model_validate(investigation).model_dump(),
        "entities_count": entities_count,
        "relationships_count": relationships_count,
        "risk_count": risk_count,
        "timeline": [],
    }


@websocket_router.websocket("/ws/investigations/{investigation_id}")
async def investigation_progress(websocket: WebSocket, investigation_id: UUID) -> None:
    origin = websocket.headers.get("origin")
    if origin and origin.rstrip("/") not in settings.allowed_origins:
        await websocket.close(code=1008, reason="Origin is not allowed")
        return
    await websocket.accept()
    try:
        with Session(get_engine()) as db:
            row = db.get(Investigation, investigation_id)
        if row is None:
            await websocket.send_json({"type": "error", "message": "Investigation not found"})
            await websocket.close(code=1008)
            return
        await websocket.send_json(
            {
                "type": "snapshot",
                "investigation": InvestigationRead.model_validate(row).model_dump(mode="json"),
                "message": "Current persisted status. No agent worker is configured.",
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await websocket.send_json(
                {"type": "error", "message": "Investigation progress is unavailable"}
            )
            await websocket.close(code=1013)
        except RuntimeError:
            return
