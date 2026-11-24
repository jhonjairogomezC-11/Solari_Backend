"""Stream de notificaciones en vivo (Server-Sent Events).

Cada conexión consulta la base cada `POLL_SEGUNDOS` con una sesión corta (no
retiene conexiones del pool) y emite `event: notificacion` solo cuando cambia el
conteo de no leídas. Si no hay cambios envía un comentario de latido cada
`HEARTBEAT_SEGUNDOS` para que proxies y navegador no cierren la conexión. La
conexión se cierra sola tras `DURACION_MAX_SEGUNDOS`; el cliente reconecta con un
ticket nuevo, lo que vuelve a validar que la cuenta siga activa.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.notificacion import Notificacion
from app.repositories.notificacion_repo import NotificacionRepository
from app.schemas.notificacion import NotificacionOut

logger = logging.getLogger("solari.sse")

POLL_SEGUNDOS = 5.0
HEARTBEAT_SEGUNDOS = 25.0
DURACION_MAX_SEGUNDOS = 15 * 60
EVENTO = "notificacion"


def formatear_evento(evento: str, data: dict[str, Any]) -> str:
    """Serializa un evento SSE (una sola línea `data:` con JSON compacto)."""
    cuerpo = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
    return f"event: {evento}\ndata: {cuerpo}\n\n"


def latido() -> str:
    return ": ping\n\n"


async def _estado_actual(
    usuario_id: uuid.UUID, incluir_ultima: bool
) -> tuple[int, dict[str, Any] | None]:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        total = await NotificacionRepository(db).no_leidas_count(usuario_id)
        ultima = None
        if incluir_ultima:
            notif = (
                await db.execute(
                    select(Notificacion)
                    .where(Notificacion.usuario_id == usuario_id)
                    .order_by(Notificacion.fecha_creacion.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if notif is not None:
                ultima = NotificacionOut.model_validate(notif).model_dump(mode="json")
        return total, ultima


async def eventos_notificaciones(
    usuario_id: uuid.UUID,
    desconectado: Callable[[], Awaitable[bool]],
) -> AsyncIterator[str]:
    """Generador de eventos SSE para un usuario."""
    yield "retry: 5000\n\n"
    ultimo: int | None = None
    inicio = time.monotonic()
    ultimo_envio = inicio
    while True:
        if await desconectado():
            break
        ahora = time.monotonic()
        if ahora - inicio >= DURACION_MAX_SEGUNDOS:
            break
        try:
            total, _ = await _estado_actual(usuario_id, incluir_ultima=False)
            if total != ultimo:
                data: dict[str, Any] = {"no_leidas": total}
                # Solo si aumentó hay una notificación nueva que mostrar.
                if ultimo is not None and total > ultimo:
                    total, ultima = await _estado_actual(usuario_id, incluir_ultima=True)
                    data = {"no_leidas": total, "ultima": ultima}
                ultimo = total
                ultimo_envio = ahora
                yield formatear_evento(EVENTO, data)
        except SQLAlchemyError:
            logger.warning("No se pudo consultar notificaciones para el stream", exc_info=True)
        if time.monotonic() - ultimo_envio >= HEARTBEAT_SEGUNDOS:
            ultimo_envio = time.monotonic()
            yield latido()
        await asyncio.sleep(POLL_SEGUNDOS)
