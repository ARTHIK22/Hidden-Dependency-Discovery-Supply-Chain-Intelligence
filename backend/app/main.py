import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.v1.investigations import websocket_router
from app.core.config import settings
from app.core.database import get_engine
from app.models import Base  # Importing the package registers every table.

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create missing tables for a local development database. This is not a
    # schema migration mechanism; production deployments need managed migrations.
    if settings.app_env.lower() in {"development", "dev", "local"} and settings.database_url:
        try:
            Base.metadata.create_all(bind=get_engine())
        except Exception:
            logger.warning("Development database initialization failed; check DATABASE_URL and PostgreSQL availability.")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
app.include_router(api_router, prefix="/api")
app.include_router(websocket_router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "health": "/api/health"}
