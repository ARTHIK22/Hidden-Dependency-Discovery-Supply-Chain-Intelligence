from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from app.core.logging import get_logger, setup_logging
from app.core.middleware import request_logging_middleware


# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------

setup_logging()
logger = get_logger(__name__)


# ---------------------------------------------------------
# APPLICATION LIFESPAN
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s v%s",
        settings.APP_NAME,
        settings.APP_VERSION,
    )

    logger.info("Environment: %s", settings.APP_ENV)

    yield

    logger.info("Shutting down backend")


# ---------------------------------------------------------
# FASTAPI APPLICATION
# ---------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend API for Hidden Dependency Intelligence. "
        "The system discovers, verifies, analyzes and "
        "visualizes hidden dependencies between entities."
    ),
    debug=settings.DEBUG,
    lifespan=lifespan,
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# REQUEST LOGGING
# ---------------------------------------------------------

app.middleware("http")(request_logging_middleware)


# ---------------------------------------------------------
# EXCEPTION HANDLERS
# ---------------------------------------------------------

app.add_exception_handler(
    AppException,
    app_exception_handler,
)

app.add_exception_handler(
    StarletteHTTPException,
    http_exception_handler,
)

app.add_exception_handler(
    HTTPException,
    http_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

app.add_exception_handler(
    Exception,
    unexpected_exception_handler,
)


# ---------------------------------------------------------
# API ROUTES
# ---------------------------------------------------------

app.include_router(api_router)


# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------

@app.get("/", tags=["System"])
async def root():
    return {
        "success": True,
        "message": "Hidden Dependency Intelligence API",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "docs": "/docs",
        "health": "/api/v1/health",
    }


# ---------------------------------------------------------
# API INFORMATION
# ---------------------------------------------------------

@app.get("/api", tags=["System"])
async def api_info():
    return {
        "success": True,
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api_version": "v1",
        "status": "online",
    }


# ---------------------------------------------------------
# CORS DEBUG
# ---------------------------------------------------------

@app.get("/api/v1/cors-test", tags=["System"])
async def cors_test():
    return {
        "success": True,
        "message": "CORS is working correctly",
        "allowed_frontend": [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
    }
