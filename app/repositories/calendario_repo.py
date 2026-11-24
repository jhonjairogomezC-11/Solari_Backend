"""Consultas del calendario de actividades y de los recordatorios."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogo import Municipio
from app.models.fundacion import Fundacion
from app.models.notificacion import Notificacion
from app.models.postulacion import ESTADO_ACEPTADO, ESTADO_ASISTIO, Postulacion
from app.models.publicacion import ESTADO_CANCELADA, ESTADO_PUBLICADA, Publicacion
from app.models.voluntario import Voluntario

# Clave fija del bloqueo consultivo que evita ejecuciones simultáneas de recordatorios.
_LOCK_RECORDATORIOS = 728_431_001


class CalendarioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def actividades_voluntario(
        self,
        voluntario_id: uuid.UUID,
        estados: Sequence[str],
        desde: date,
        hasta: date | None,
    ) -> list[Any]:
        """Filas (Postulacion, Publicacion, nombre_fundacion, nombre_municipio)."""
        stmt = (
            select(Postulacion, Publicacion, Fundacion.nombre, Municipio.nombre)
            .join(Publicacion, Publicacion.id == Postulacion.publicacion_id)
            .join(Fundacion, Fundacion.id == Publicacion.fundacion_id)
            .outerjoin(Municipio, Municipio.id == Publicacion.municipio_id)
            .where(
                Postulacion.voluntario_id == voluntario_id,
                Postulacion.estado.in_(list(estados)),
                Publicacion.estado != ESTADO_CANCELADA,
                Publicacion.fecha_fin >= desde,
            )
            .order_by(Publicacion.fecha_inicio, Publicacion.hora_inicio)
        )
        if hasta is not None:
            stmt = stmt.where(Publicacion.fecha_inicio <= hasta)
        return list((await self.db.execute(stmt)).all())

    async def actividades_fundacion(
        self, fundacion_id: uuid.UUID, desde: date, hasta: date
    ) -> list[Any]:
        """Filas (Publicacion, nombre_fundacion, nombre_municipio, aceptados)."""
        aceptados = (
            select(func.count(Postulacion.id))
            .where(
                Postulacion.publicacion_id == Publicacion.id,
                Postulacion.estado.in_([ESTADO_ACEPTADO, ESTADO_ASISTIO]),
            )
            .correlate(Publicacion)
            .scalar_subquery()
        )
        stmt = (
            select(Publicacion, Fundacion.nombre, Municipio.nombre, aceptados)
            .join(Fundacion, Fundacion.id == Publicacion.fundacion_id)
            .outerjoin(Municipio, Municipio.id == Publicacion.municipio_id)
            .where(
                Publicacion.fundacion_id == fundacion_id,
                Publicacion.estado == ESTADO_PUBLICADA,
                Publicacion.fecha_fin >= desde,
                Publicacion.fecha_inicio <= hasta,
            )
            .order_by(Publicacion.fecha_inicio, Publicacion.hora_inicio)
        )
        return list((await self.db.execute(stmt)).all())

    # ── Recordatorios ──

    async def bloquear_recordatorios(self) -> bool:
        """Bloqueo consultivo de transacción: False si otro proceso ya los ejecuta."""
        res = await self.db.execute(
            text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": _LOCK_RECORDATORIOS}
        )
        return bool(res.scalar())

    async def aceptadas_que_inician(self, dia: date) -> list[Any]:
        """Filas (Postulacion, Publicacion, usuario_id del voluntario, nombre_fundacion)."""
        stmt = (
            select(Postulacion, Publicacion, Voluntario.usuario_id, Fundacion.nombre)
            .join(Publicacion, Publicacion.id == Postulacion.publicacion_id)
            .join(Voluntario, Voluntario.id == Postulacion.voluntario_id)
            .join(Fundacion, Fundacion.id == Publicacion.fundacion_id)
            .where(
                Postulacion.estado == ESTADO_ACEPTADO,
                Publicacion.estado == ESTADO_PUBLICADA,
                Publicacion.fecha_inicio == dia,
            )
        )
        return list((await self.db.execute(stmt)).all())

    async def postulaciones_ya_recordadas(
        self, tipo: str, postulacion_ids: Sequence[uuid.UUID]
    ) -> set[tuple[uuid.UUID, uuid.UUID]]:
        """Pares (usuario_id, postulacion_id) que ya tienen la notificación."""
        if not postulacion_ids:
            return set()
        stmt = select(Notificacion.usuario_id, Notificacion.objeto_id).where(
            Notificacion.tipo == tipo,
            Notificacion.objeto_tipo == "postulacion",
            Notificacion.objeto_id.in_(list(postulacion_ids)),
        )
        return {(u, o) for u, o in (await self.db.execute(stmt)).all()}
