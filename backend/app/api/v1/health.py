from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str | bool]:
    database_status = "not_configured"
    if settings.database_url:
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            database_status = "connected"
        except Exception:
            database_status = "unavailable"
    return {
        "status": "ok" if database_status == "connected" else "degraded",
        "database": database_status,
        "environment": settings.app_env,
        "demo_mode": settings.development_demo_mode,
    }
