import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends

from app.api.router import api_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.investigations import websocket_router
from app.core.config import settings
from app.api.dependencies import get_current_user
from app.services.monitoring_scheduler import monitoring_scheduler_loop


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler_task = None
    if settings.monitoring_scheduler_enabled:
        scheduler_task = asyncio.create_task(monitoring_scheduler_loop())
    try:
        yield
    finally:
        if scheduler_task is not None:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass


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
    allow_headers=["Content-Type", "Accept", "Authorization"],
)
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(api_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(websocket_router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "health": "/api/health"}
