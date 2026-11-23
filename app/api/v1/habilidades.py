"""Habilidades del voluntario (catálogo común y selección propia)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbDep, get_voluntario_actual
from app.models.voluntario import Voluntario
from app.schemas.habilidad import HabilidadesInput
from app.services.habilidad_service import HabilidadService

router = APIRouter(tags=["habilidades"])

VoluntarioDep = Annotated[Voluntario, Depends(get_voluntario_actual)]


@router.get("/mis-habilidades", response_model=list[int])
async def mis_habilidades(db: DbDep, voluntario: VoluntarioDep):
    return await HabilidadService(db).ids_de_voluntario(voluntario.id)


@router.put("/mis-habilidades", response_model=list[int])
async def guardar_mis_habilidades(db: DbDep, voluntario: VoluntarioDep, data: HabilidadesInput):
    return await HabilidadService(db).guardar_de_voluntario(voluntario.id, data.habilidad_ids)
