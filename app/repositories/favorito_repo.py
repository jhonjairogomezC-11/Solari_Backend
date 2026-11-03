"""Acceso a datos de favoritos de voluntarios."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorito import TIPO_FUNDACION, TIPO_PUBLICACION, VoluntarioFavorito


class FavoritoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def por_publicacion(
        self, voluntario_id: uuid.UUID, publicacion_id: uuid.UUID
    ) -> VoluntarioFavorito | None:
        stmt = select(VoluntarioFavorito).where(
            VoluntarioFavorito.voluntario_id == voluntario_id,
            VoluntarioFavorito.publicacion_id == publicacion_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def por_fundacion(
        self, voluntario_id: uuid.UUID, fundacion_id: uuid.UUID
    ) -> VoluntarioFavorito | None:
        stmt = select(VoluntarioFavorito).where(
            VoluntarioFavorito.voluntario_id == voluntario_id,
            VoluntarioFavorito.fundacion_id == fundacion_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def crear_publicacion(
        self, voluntario_id: uuid.UUID, publicacion_id: uuid.UUID
    ) -> VoluntarioFavorito:
        fav = VoluntarioFavorito(
            voluntario_id=voluntario_id,
            tipo=TIPO_PUBLICACION,
            publicacion_id=publicacion_id,
        )
        self.db.add(fav)
        await self.db.flush()
        return fav

    async def crear_fundacion(
        self, voluntario_id: uuid.UUID, fundacion_id: uuid.UUID
    ) -> VoluntarioFavorito:
        fav = VoluntarioFavorito(
            voluntario_id=voluntario_id,
            tipo=TIPO_FUNDACION,
            fundacion_id=fundacion_id,
        )
        self.db.add(fav)
        await self.db.flush()
        return fav

    async def eliminar(self, fav: VoluntarioFavorito) -> None:
        await self.db.delete(fav)
        await self.db.flush()

    async def listar(
        self, voluntario_id: uuid.UUID, tipo: str | None = None
    ) -> list[VoluntarioFavorito]:
        stmt = select(VoluntarioFavorito).where(
            VoluntarioFavorito.voluntario_id == voluntario_id
        )
        if tipo:
            stmt = stmt.where(VoluntarioFavorito.tipo == tipo)
        stmt = stmt.order_by(VoluntarioFavorito.fecha_creacion.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def ids_publicaciones(self, voluntario_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(VoluntarioFavorito.publicacion_id).where(
            VoluntarioFavorito.voluntario_id == voluntario_id,
            VoluntarioFavorito.tipo == TIPO_PUBLICACION,
        )
        return [r for r in (await self.db.execute(stmt)).scalars().all() if r is not None]
