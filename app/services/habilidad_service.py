"""Habilidades del voluntario y validación del rango permitido (regla R3)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.catalogo import Habilidad
from app.models.habilidades import MAX_HABILIDADES, MIN_HABILIDADES, VoluntarioHabilidad


class HabilidadService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def catalogo(self) -> list[Habilidad]:
        stmt = select(Habilidad).order_by(Habilidad.categoria, Habilidad.nombre)
        return list((await self.db.execute(stmt)).scalars().all())

    async def ids_de_voluntario(self, voluntario_id: uuid.UUID) -> list[int]:
        stmt = select(VoluntarioHabilidad.habilidad_id).where(
            VoluntarioHabilidad.voluntario_id == voluntario_id
        )
        return [r for r in (await self.db.execute(stmt)).scalars().all()]

    async def validar_ids(self, ids: list[int], *, minimo: int, maximo: int, sujeto: str) -> list[int]:
        """Elimina duplicados, comprueba existencia y rango [minimo, maximo]."""
        unicos = list(dict.fromkeys(ids))
        if not minimo <= len(unicos) <= maximo:
            raise AppError(f"{sujeto} debe tener entre {minimo} y {maximo} habilidades.", 422)
        existentes = set(
            (await self.db.execute(select(Habilidad.id).where(Habilidad.id.in_(unicos))))
            .scalars()
            .all()
        )
        faltan = [i for i in unicos if i not in existentes]
        if faltan:
            raise AppError(f"Hay habilidades que no existen: {faltan}.", 422)
        return unicos

    async def guardar_de_voluntario(
        self, voluntario_id: uuid.UUID, ids: list[int]
    ) -> list[int]:
        unicos = await self.validar_ids(
            ids, minimo=MIN_HABILIDADES, maximo=MAX_HABILIDADES, sujeto="El voluntario"
        )
        await self.db.execute(
            delete(VoluntarioHabilidad).where(VoluntarioHabilidad.voluntario_id == voluntario_id)
        )
        for hid in unicos:
            self.db.add(VoluntarioHabilidad(voluntario_id=voluntario_id, habilidad_id=hid))
        await self.db.commit()
        return unicos
