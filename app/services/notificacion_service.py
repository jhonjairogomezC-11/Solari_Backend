"""Servicio de notificaciones.

Las notificaciones respetan las preferencias del usuario: si desactivó una
categoría, el evento no genera notificación. Los avisos de cuenta y de
verificación institucional se envían siempre (son importantes).
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cuenta import PreferenciasNotificacion
from app.models.notificacion import Notificacion
from app.repositories.notificacion_repo import NotificacionRepository

# tipo de notificación -> columna de preferencia que la controla.
_CATEGORIA: dict[str, str] = {
    "NUEVA_POSTULACION": "notif_postulaciones",
    "POSTULACION_RETIRADA": "notif_postulaciones",
    "POSTULACION_ACEPTADA": "notif_postulaciones",
    "POSTULACION_RECHAZADA": "notif_postulaciones",
    "VOLUNTARIO_ASISTIO": "notif_postulaciones",
    "VOLUNTARIO_NO_ASISTIO": "notif_postulaciones",
    "ACTIVIDAD_CANCELADA": "notif_postulaciones",
    "ACTIVIDAD_MODIFICADA": "notif_postulaciones",
    "NUEVA_CONVOCATORIA_COMPATIBLE": "notif_convocatorias",
    "POSTULACION_ACTUALIZADA": "notif_postulaciones",
    "PROGRAMACION_PAUSADA": "notif_convocatorias",
    "RECORDATORIO_ACTIVIDAD": "notif_recordatorios",
    "LOGRO_DESBLOQUEADO": "notif_logros",
    "XP_OBTENIDO": "notif_logros",
    "RESPUESTA_SOPORTE": "notif_soporte",
}


class NotificacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificacionRepository(db)

    async def _permitida(self, usuario_id: uuid.UUID, tipo: str) -> bool:
        columna = _CATEGORIA.get(tipo)
        if columna is None:
            return True  # avisos críticos o sin categoría: siempre
        pref = await self.db.get(PreferenciasNotificacion, usuario_id)
        if pref is None:
            return True  # sin preferencias guardadas: todo habilitado
        return bool(getattr(pref, columna))

    async def notificar(
        self,
        usuario_id: uuid.UUID,
        tipo: str,
        mensaje: str,
        objeto_tipo: str | None = None,
        objeto_id: uuid.UUID | None = None,
    ) -> Notificacion | None:
        if not await self._permitida(usuario_id, tipo):
            return None
        return await self.repo.crear(usuario_id, tipo, mensaje, objeto_tipo, objeto_id)

    async def listar(self, usuario_id: uuid.UUID, page: int, per_page: int):
        return await self.repo.listar(usuario_id, page, per_page)

    async def no_leidas(self, usuario_id: uuid.UUID) -> int:
        return await self.repo.no_leidas_count(usuario_id)

    async def marcar_leida(self, notificacion_id: uuid.UUID, usuario_id: uuid.UUID):
        notif = await self.repo.marcar_leida(notificacion_id, usuario_id)
        await self.db.commit()
        return notif

    async def marcar_todas_leidas(self, usuario_id: uuid.UUID) -> int:
        n = await self.repo.marcar_todas_leidas(usuario_id)
        await self.db.commit()
        return n
