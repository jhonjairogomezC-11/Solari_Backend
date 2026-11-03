"""Endpoints de catálogos (públicos, solo lectura)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbDep
from app.repositories.catalogo_repo import CatalogoRepository
from app.schemas.catalogo import (
    AreaImpactoOut,
    DepartamentoOut,
    HabilidadOut,
    MunicipioOut,
)

router = APIRouter(prefix="/catalogos", tags=["catalogos"])


@router.get("/departamentos", response_model=list[DepartamentoOut])
async def departamentos(db: DbDep):
    return await CatalogoRepository(db).departamentos()


@router.get("/municipios", response_model=list[MunicipioOut])
async def municipios(db: DbDep, departamento_id: int | None = None):
    return await CatalogoRepository(db).municipios(departamento_id)


@router.get("/areas-impacto", response_model=list[AreaImpactoOut])
async def areas_impacto(db: DbDep):
    return await CatalogoRepository(db).areas_impacto()


@router.get("/habilidades", response_model=list[HabilidadOut])
async def habilidades(db: DbDep):
    return await CatalogoRepository(db).habilidades()
