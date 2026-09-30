# backend/app/core/database.py

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine_options = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
    if settings.DATABASE_URL.endswith("://"):
        engine_options["poolclass"] = StaticPool
else:
    engine_options["connect_args"] = {"connect_timeout": 5}

engine = create_engine(settings.DATABASE_URL, **engine_options)


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
