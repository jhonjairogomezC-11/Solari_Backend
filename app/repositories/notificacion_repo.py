"""Acceso a datos de notificaciones."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notificacion import Notificacion


def _now() -> datetime:
    return datetime.now(UTC)


class NotificacionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear(
        self,
        usuario_id: uuid.UUID,
        tipo: str,
        mensaje: str,
        objeto_tipo: str | None = None,
        objeto_id: uuid.UUID | None = None,
    ) -> Notificacion:
        notif = Notificacion(
            usuario_id=usuario_id,
            tipo=tipo,
            mensaje=mensaje,
            objeto_tipo=objeto_tipo,
            objeto_id=objeto_id,
        )
        self.db.add(notif)
        await self.db.flush()
        return notif

    async def listar(
        self, usuario_id: uuid.UUID, page: int = 1, per_page: int = 20
    ) -> tuple[list[Notificacion], int]:
        base = select(Notificacion).where(Notificacion.usuario_id == usuario_id)
        total = (
            await self.db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = (
            base.order_by(Notificacion.fecha_creacion.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        filas = list((await self.db.execute(stmt)).scalars().all())
        return filas, total

    async def no_leidas_count(self, usuario_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Notificacion).where(
            Notificacion.usuario_id == usuario_id,
            Notificacion.leida.is_(False),
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def marcar_leida(
        self, notificacion_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> Notificacion | None:
        notif = await self.db.get(Notificacion, notificacion_id)
        if notif is None or notif.usuario_id != usuario_id:
            return None
        notif.leida = True
        notif.fecha_lectura = _now()
        await self.db.flush()
        return notif

    async def marcar_todas_leidas(self, usuario_id: uuid.UUID) -> int:
        stmt = (
            update(Notificacion)
            .where(Notificacion.usuario_id == usuario_id, Notificacion.leida.is_(False))
            .values(leida=True, fecha_lectura=_now())
        )
        result = await self.db.execute(stmt)
        return result.rowcount or 0
