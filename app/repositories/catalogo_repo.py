"""Acceso a datos de catálogos (solo lectura)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalogo import AreaImpacto, Departamento, Habilidad, Municipio


class CatalogoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def departamentos(self) -> list[Departamento]:
        stmt = select(Departamento).order_by(Departamento.nombre)
        return list((await self.db.execute(stmt)).scalars().all())

    async def municipios(self, departamento_id: int | None = None) -> list[Municipio]:
        stmt = (
            select(Municipio)
            .options(selectinload(Municipio.departamento))
            .order_by(Municipio.nombre)
        )
        if departamento_id:
            stmt = stmt.where(Municipio.departamento_id == departamento_id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def areas_impacto(self) -> list[AreaImpacto]:
        stmt = select(AreaImpacto).order_by(AreaImpacto.nombre)
        return list((await self.db.execute(stmt)).scalars().all())

    async def habilidades(self) -> list[Habilidad]:
        stmt = select(Habilidad).order_by(Habilidad.nombre)
        return list((await self.db.execute(stmt)).scalars().all())
