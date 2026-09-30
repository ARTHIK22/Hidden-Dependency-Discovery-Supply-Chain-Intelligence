from collections.abc import Generator
from threading import Lock

from fastapi import HTTPException
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import settings

_engine: Engine | None = None
_engine_lock = Lock()


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    with _engine_lock:
        if _engine is None:
            _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def get_db() -> Generator[Session, None, None]:
    try:
        engine = get_engine()
        session = Session(engine)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable. Check the backend database configuration and service.",
        ) from exc
    try:
        yield session
    except OperationalError as exc:
        session.rollback()
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable. Check the backend database configuration and service.",
        ) from exc
    finally:
        session.close()
