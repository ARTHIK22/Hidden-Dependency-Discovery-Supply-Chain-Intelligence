from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.investigations import router as investigation_router
from app.core.config import settings


app = FastAPI(
	title=settings.APP_NAME,
	version="1.0.0",
	description="Agentic supply-chain dependency discovery and intelligence platform.",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:5173"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.API_PREFIX)
app.include_router(investigation_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
	return {"name": settings.APP_NAME, "status": "running", "version": "1.0.0"}
