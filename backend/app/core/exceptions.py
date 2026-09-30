# backend/app/core/exceptions.py

import logging

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "APP_ERROR",
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"success": False, "error": {"code": f"HTTP_{exc.status_code}", "message": detail}},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"location": list(item.get("loc", ())), "message": item.get("msg", "Invalid value"), "type": item.get("type", "value_error")}
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": errors}},
    )


async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("app.errors").exception("Unhandled error for %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_SERVER_ERROR", "message": "An internal error occurred"}},
    )
