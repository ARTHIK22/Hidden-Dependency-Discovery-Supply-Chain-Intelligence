from fastapi import APIRouter

from app.api.v1.alerts import router as alerts_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.entities import router as entities_router, search_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.graph import router as graph_router
from app.api.v1.health import router as health_router
from app.api.v1.investigations import router as investigations_router
from app.api.v1.reports import router as reports_router
from app.api.v1.risks import router as risks_router
from app.api.v1.watchlists import router as watchlists_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(dashboard_router)
api_router.include_router(investigations_router)
api_router.include_router(entities_router)
api_router.include_router(search_router)
api_router.include_router(evidence_router)
api_router.include_router(graph_router)
api_router.include_router(risks_router)
api_router.include_router(alerts_router)
api_router.include_router(watchlists_router)
api_router.include_router(reports_router)
