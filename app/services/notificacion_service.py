"""Servicio de notificaciones."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notificacion import Notificacion
from app.repositories.notificacion_repo import NotificacionRepository


class NotificacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificacionRepository(db)

    async def notificar(
        self,
        usuario_id: uuid.UUID,
        tipo: str,
        mensaje: str,
        objeto_tipo: str | None = None,
        objeto_id: uuid.UUID | None = None,
    ) -> Notificacion:
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
