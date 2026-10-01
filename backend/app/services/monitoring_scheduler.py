"""Opt-in single-process scheduler for enabled investigation monitors."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.services.monitoring_service import run_due_monitoring_once


logger = logging.getLogger(__name__)


async def monitoring_scheduler_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(run_due_monitoring_once)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduled investigation monitoring pass failed")
        await asyncio.sleep(settings.monitoring_scheduler_tick_seconds)
