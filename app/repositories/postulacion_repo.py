"""Acceso a datos de postulaciones."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postulacion import ESTADO_LISTA_ESPERA, ESTADO_PENDIENTE, Postulacion


class PostulacionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def existe(self, publicacion_id: uuid.UUID, voluntario_id: uuid.UUID) -> bool:
        stmt = select(Postulacion.id).where(
            Postulacion.publicacion_id == publicacion_id,
            Postulacion.voluntario_id == voluntario_id,
        )
        return (await self.db.execute(stmt)).first() is not None

    async def crear(
        self,
        publicacion_id: uuid.UUID,
        voluntario_id: uuid.UUID,
        mensaje: str | None,
        lista_espera: bool = False,
    ) -> Postulacion:
        post = Postulacion(
            publicacion_id=publicacion_id,
            voluntario_id=voluntario_id,
            estado=ESTADO_LISTA_ESPERA if lista_espera else ESTADO_PENDIENTE,
            mensaje_voluntario=mensaje,
        )
        self.db.add(post)
        await self.db.flush()
        return post

    async def por_id(self, postulacion_id: uuid.UUID) -> Postulacion | None:
        return await self.db.get(Postulacion, postulacion_id)

    async def mis_postulaciones(
        self, voluntario_id: uuid.UUID, page: int = 1, per_page: int = 15
    ) -> tuple[list[Postulacion], int]:
        base = select(Postulacion).where(Postulacion.voluntario_id == voluntario_id)
        total = (
            await self.db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = (
            base.order_by(Postulacion.fecha_postulacion.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        filas = list((await self.db.execute(stmt)).scalars().all())
        return filas, total

    async def de_publicacion(
        self, publicacion_id: uuid.UUID, page: int = 1, per_page: int = 15
    ) -> tuple[list[Postulacion], int]:
        base = select(Postulacion).where(Postulacion.publicacion_id == publicacion_id)
        total = (
            await self.db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = (
            base.order_by(Postulacion.fecha_postulacion.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        filas = list((await self.db.execute(stmt)).scalars().all())
        return filas, total

    async def contar_por_estado(self, publicacion_id: uuid.UUID, estado: str) -> int:
        stmt = select(func.count()).select_from(Postulacion).where(
            Postulacion.publicacion_id == publicacion_id,
            Postulacion.estado == estado,
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def contar_aceptadas(self, publicacion_id: uuid.UUID) -> int:
        from app.models.postulacion import ESTADO_ACEPTADO, ESTADO_ASISTIO

        stmt = select(func.count()).select_from(Postulacion).where(
            Postulacion.publicacion_id == publicacion_id,
            Postulacion.estado.in_([ESTADO_ACEPTADO, ESTADO_ASISTIO]),
        )
        return (await self.db.execute(stmt)).scalar_one()
