"""Acceso a datos de los mensajes dentro de una postulación."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fundacion import Fundacion
from app.models.mensaje_postulacion import MensajePostulacion
from app.models.postulacion import Postulacion
from app.models.publicacion import Publicacion
from app.models.voluntario import Voluntario


class MensajePostulacionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def contexto(
        self, postulacion_id: uuid.UUID
    ) -> tuple[Postulacion, Publicacion, Voluntario, Fundacion] | None:
        """Postulación con su convocatoria, voluntario y organización (o None)."""
        stmt = (
            select(Postulacion, Publicacion, Voluntario, Fundacion)
            .join(Publicacion, Publicacion.id == Postulacion.publicacion_id)
            .join(Voluntario, Voluntario.id == Postulacion.voluntario_id)
            .join(Fundacion, Fundacion.id == Publicacion.fundacion_id)
            .where(Postulacion.id == postulacion_id)
        )
        fila = (await self.db.execute(stmt)).first()
        if fila is None:
            return None
        return fila[0], fila[1], fila[2], fila[3]

    async def listar(self, postulacion_id: uuid.UUID) -> list[MensajePostulacion]:
        stmt = (
            select(MensajePostulacion)
            .where(MensajePostulacion.postulacion_id == postulacion_id)
            .order_by(MensajePostulacion.fecha_creacion, MensajePostulacion.id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def crear(
        self, postulacion_id: uuid.UUID, autor_id: uuid.UUID, mensaje: str
    ) -> MensajePostulacion:
        msg = MensajePostulacion(
            postulacion_id=postulacion_id, autor_id=autor_id, mensaje=mensaje, leido=False
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def marcar_leidos_de_otros(
        self, postulacion_id: uuid.UUID, lector_id: uuid.UUID
    ) -> int:
        stmt = (
            update(MensajePostulacion)
            .where(
                MensajePostulacion.postulacion_id == postulacion_id,
                MensajePostulacion.autor_id != lector_id,
                MensajePostulacion.leido.is_(False),
            )
            .values(leido=True)
        )
        result = await self.db.execute(stmt)
        return result.rowcount or 0

    async def no_leidos_count(self, usuario_id: uuid.UUID) -> int:
        """Mensajes de la contraparte sin leer en postulaciones donde participa el usuario."""
        stmt = (
            select(func.count(MensajePostulacion.id))
            .join(Postulacion, Postulacion.id == MensajePostulacion.postulacion_id)
            .join(Voluntario, Voluntario.id == Postulacion.voluntario_id)
            .join(Publicacion, Publicacion.id == Postulacion.publicacion_id)
            .join(Fundacion, Fundacion.id == Publicacion.fundacion_id)
            .where(
                MensajePostulacion.leido.is_(False),
                MensajePostulacion.autor_id != usuario_id,
                or_(Voluntario.usuario_id == usuario_id, Fundacion.usuario_id == usuario_id),
            )
        )
        return (await self.db.execute(stmt)).scalar_one()
