# backend/app/api/v1/health.py

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal
from app.core.redis import check_redis_connection

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("")
async def health_check():
    database_status = "connected"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database_status = "unavailable"
    return {
        "success": database_status == "connected",
        "status": "healthy" if database_status == "connected" else "degraded",
        "service": "hidden-dependency-intelligence-backend",
        "version": "0.1.0",
        "database": database_status,
        "redis": "available" if check_redis_connection() else "unavailable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness_check():
    redis_status = check_redis_connection()
    database_status = "connected"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database_status = "unavailable"

    return {
        "success": True,
        "status": "ready" if database_status == "connected" else "unavailable",
        "services": {
            "api": "up",
            "database": database_status,
            "redis": "up" if redis_status else "unavailable",
        },
    }
