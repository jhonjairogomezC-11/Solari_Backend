"""Tareas de fondo de la aplicación (ciclo de vida de FastAPI)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_ENTORNOS_SIN_TAREAS = {"testing", "test", "ci"}


def recordatorios_activos(settings: Settings) -> bool:
    return settings.reminders_enabled and settings.app_env.lower() not in _ENTORNOS_SIN_TAREAS


@asynccontextmanager
async def lifespan_tareas(_: FastAPI) -> AsyncIterator[None]:
    """Arranca el bucle de recordatorios (cada hora) y lo detiene al apagar."""
    tarea: asyncio.Task[None] | None = None
    if recordatorios_activos(get_settings()):
        from app.services.recordatorio_service import bucle_recordatorios

        tarea = asyncio.create_task(bucle_recordatorios(), name="recordatorios")
        logger.info("Tarea de recordatorios de actividad iniciada (cada hora).")
    try:
        yield
    finally:
        if tarea is not None:
            tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tarea
