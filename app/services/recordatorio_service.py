"""Recordatorios de actividades: avisa un día antes a los voluntarios aceptados.

La ejecución es idempotente: una postulación recibe a lo sumo un recordatorio
(se busca una notificación previa con el mismo usuario, tipo y postulación).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notificacion import TIPO_RECORDATORIO_ACTIVIDAD
from app.repositories.calendario_repo import CalendarioRepository
from app.services.calendario_service import hoy_bogota
from app.services.notificacion_service import NotificacionService

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 3600
ESPERA_INICIAL_SEGUNDOS = 30


def fecha_recordatorio(ahora: datetime | None = None) -> date:
    """Día de inicio de las actividades a recordar: mañana en hora de Bogotá."""
    return hoy_bogota(ahora) + timedelta(days=1)


def mensaje_recordatorio(
    titulo: str, organizacion: str, dia: date, hora_inicio=None
) -> str:
    hora = f" a las {hora_inicio:%H:%M}" if hora_inicio else ""
    return (
        f"Recordatorio: mañana {dia:%d/%m/%Y}{hora} participas en «{titulo}» "
        f"con {organizacion}. ¡Gracias por tu tiempo!"
    )


class RecordatorioService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CalendarioRepository(db)
        self.notif = NotificacionService(db)

    async def ejecutar(self, ahora: datetime | None = None) -> int:
        """Crea los recordatorios pendientes y devuelve cuántos se crearon."""
        if not await self.repo.bloquear_recordatorios():
            logger.info("Recordatorios: otra ejecución está en curso; se omite.")
            await self.db.rollback()
            return 0
        dia = fecha_recordatorio(ahora)
        filas = await self.repo.aceptadas_que_inician(dia)
        ya = await self.repo.postulaciones_ya_recordadas(
            TIPO_RECORDATORIO_ACTIVIDAD, [post.id for post, *_ in filas]
        )
        creados = 0
        for post, pub, usuario_id, org in filas:
            if (usuario_id, post.id) in ya:
                continue
            notif = await self.notif.notificar(
                usuario_id,
                TIPO_RECORDATORIO_ACTIVIDAD,
                mensaje_recordatorio(pub.titulo, org, dia, pub.hora_inicio),
                "postulacion",
                post.id,
            )
            if notif is not None:
                creados += 1
                ya.add((usuario_id, post.id))
        # El commit libera también el bloqueo consultivo de la transacción.
        await self.db.commit()
        return creados


async def ejecutar_recordatorios() -> int:
    """Ejecuta una pasada con una sesión propia (para la tarea de fondo)."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        return await RecordatorioService(session).ejecutar()


async def bucle_recordatorios(intervalo: int = INTERVALO_SEGUNDOS) -> None:
    """Tarea de fondo: ejecuta los recordatorios cada `intervalo` segundos.

    Los errores se registran y no detienen el bucle.
    """
    await asyncio.sleep(ESPERA_INICIAL_SEGUNDOS)
    while True:
        try:
            creados = await ejecutar_recordatorios()
            if creados:
                logger.info("Recordatorios de actividad creados: %s", creados)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Falló la ejecución de recordatorios de actividad.")
        await asyncio.sleep(intervalo)
