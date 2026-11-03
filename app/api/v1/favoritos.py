"""Endpoints de favoritos (solo voluntarios)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbDep, get_voluntario_actual
from app.models.voluntario import Voluntario
from app.schemas.favorito import FavoritoConvocatoriaOut, ToggleResult
from app.services.favorito_service import FavoritoService

router = APIRouter(prefix="/favoritos", tags=["favoritos"])

VoluntarioDep = Annotated[Voluntario, Depends(get_voluntario_actual)]


@router.get("/convocatorias", response_model=list[FavoritoConvocatoriaOut])
async def listar_convocatorias_favoritas(db: DbDep, voluntario: VoluntarioDep):
    return await FavoritoService(db).listar_convocatorias(voluntario.id)


@router.get("/ids", response_model=list[str])
async def ids_favoritos(db: DbDep, voluntario: VoluntarioDep):
    return await FavoritoService(db).ids_publicaciones(voluntario.id)


@router.post("/convocatoria/{publicacion_id}", response_model=ToggleResult)
async def toggle_convocatoria(
    db: DbDep, voluntario: VoluntarioDep, publicacion_id: uuid.UUID
):
    favorito = await FavoritoService(db).toggle_publicacion(voluntario.id, publicacion_id)
    return ToggleResult(favorito=favorito)


@router.post("/fundacion/{fundacion_id}", response_model=ToggleResult)
async def toggle_fundacion(db: DbDep, voluntario: VoluntarioDep, fundacion_id: uuid.UUID):
    favorito = await FavoritoService(db).toggle_fundacion(voluntario.id, fundacion_id)
    return ToggleResult(favorito=favorito)
