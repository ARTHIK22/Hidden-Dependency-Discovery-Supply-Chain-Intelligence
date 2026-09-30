# backend/app/api/router.py

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.entities import router as entities_router
from app.api.v1.relationships import router as relationships_router
from app.api.v1.investigations import router as investigations_router
from app.api.v1.graph import router as graph_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.sources import router as sources_router
from app.api.v1.risks import router as risks_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.watchlists import router as watchlists_router
from app.api.v1.reports import router as reports_router
from app.api.v1.exports import router as exports_router
from app.api.v1.users import router as users_router


api_router = APIRouter(
    prefix="/api/v1",
)

api_router.include_router(
    health_router,
)
for router in (auth_router, users_router, entities_router, relationships_router, investigations_router, graph_router, evidence_router, sources_router, risks_router, alerts_router, watchlists_router, reports_router, exports_router):
    api_router.include_router(router)
