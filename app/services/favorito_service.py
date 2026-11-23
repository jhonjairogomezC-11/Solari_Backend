"""Reglas de negocio de favoritos."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.favorito import TIPO_FUNDACION, TIPO_PUBLICACION
from app.models.fundacion import Fundacion
from app.repositories.favorito_repo import FavoritoRepository
from app.repositories.publicacion_repo import PublicacionRepository
from app.schemas.favorito import (
    FavoritoConvocatoriaOut,
    FavoritoFundacionOut,
    FundacionResumenFav,
)
from app.schemas.publicacion import PublicacionOut


class FavoritoService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FavoritoRepository(db)
        self.pub_repo = PublicacionRepository(db)

    async def toggle_publicacion(
        self, voluntario_id: uuid.UUID, publicacion_id: uuid.UUID
    ) -> bool:
        """Agrega o quita de favoritos. Devuelve True si quedó marcado."""
        existente = await self.repo.por_publicacion(voluntario_id, publicacion_id)
        if existente:
            await self.repo.eliminar(existente)
            await self.db.commit()
            return False

        pub = await self.pub_repo.por_id(publicacion_id)
        if pub is None:
            raise NotFoundError("Convocatoria no encontrada.")
        await self.repo.crear_publicacion(voluntario_id, publicacion_id)
        await self.db.commit()
        return True

    async def toggle_fundacion(
        self, voluntario_id: uuid.UUID, fundacion_id: uuid.UUID
    ) -> bool:
        existente = await self.repo.por_fundacion(voluntario_id, fundacion_id)
        if existente:
            await self.repo.eliminar(existente)
            await self.db.commit()
            return False
        fundacion = await self.db.get(Fundacion, fundacion_id)
        if fundacion is None:
            raise NotFoundError("Fundación no encontrada.")
        await self.repo.crear_fundacion(voluntario_id, fundacion_id)
        await self.db.commit()
        return True

    async def listar_fundaciones(
        self, voluntario_id: uuid.UUID
    ) -> list[FavoritoFundacionOut]:
        favs = await self.repo.listar(voluntario_id, TIPO_FUNDACION)
        salida: list[FavoritoFundacionOut] = []
        for fav in favs:
            if fav.fundacion_id is None:
                continue
            fundacion = await self.db.get(Fundacion, fav.fundacion_id)
            if fundacion is None:
                continue
            salida.append(
                FavoritoFundacionOut(
                    id=fav.id,
                    fecha_creacion=fav.fecha_creacion,
                    fundacion=FundacionResumenFav.model_validate(fundacion),
                )
            )
        return salida

    async def ids_publicaciones(self, voluntario_id: uuid.UUID) -> list[str]:
        ids = await self.repo.ids_publicaciones(voluntario_id)
        return [str(i) for i in ids]

    async def listar_convocatorias(
        self, voluntario_id: uuid.UUID
    ) -> list[FavoritoConvocatoriaOut]:
        favs = await self.repo.listar(voluntario_id, TIPO_PUBLICACION)
        salida: list[FavoritoConvocatoriaOut] = []
        for fav in favs:
            if fav.publicacion_id is None:
                continue
            pub = await self.pub_repo.por_id_con_habilidades(fav.publicacion_id)
            if pub is None:
                continue
            salida.append(
                FavoritoConvocatoriaOut(
                    id=fav.id,
                    fecha_creacion=fav.fecha_creacion,
                    convocatoria=PublicacionOut.model_validate(pub),
                )
            )
        return salida
