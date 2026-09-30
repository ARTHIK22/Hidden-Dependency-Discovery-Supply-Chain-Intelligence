# backend/app/core/middleware.py

import time
from uuid import uuid4

from fastapi import Request

from app.core.logging import get_logger

logger = get_logger(__name__)


async def request_logging_middleware(
    request: Request,
    call_next,
):
    request_id = str(uuid4())
    start_time = time.perf_counter()

    response = await call_next(request)

    duration = time.perf_counter() - start_time

    response.headers["X-Request-ID"] = request_id

    logger.info(
        "%s %s -> %s | %.4fs | request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration,
        request_id,
    )

    return response