from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.source import Source
from app.models.user import User
from app.schemas.source import SourceCreate, SourceRead

router = APIRouter(prefix="/sources", tags=["Sources"])


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED, summary="Register a research source")
def create_source(payload: SourceCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    values = payload.model_dump()
    if values.get("url") is not None:
        values["url"] = str(values["url"])
    source = Source(**values)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("", response_model=list[SourceRead], summary="List registered sources")
def list_sources(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Source).order_by(Source.name).limit(limit).offset(offset)))
