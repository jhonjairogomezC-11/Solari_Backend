"""Endpoints de actividades recurrentes (solo organizaciones)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.deps import DbDep, get_fundacion_actual
from app.models.fundacion import Fundacion
from app.schemas.programacion import ProgramacionCreate, ProgramacionOut
from app.services.programacion_service import ProgramacionService

router = APIRouter(tags=["programaciones"])

FundacionDep = Annotated[Fundacion, Depends(get_fundacion_actual)]


@router.post("/programaciones", response_model=ProgramacionOut, status_code=status.HTTP_201_CREATED)
async def crear_programacion(db: DbDep, fundacion: FundacionDep, data: ProgramacionCreate):
    return await ProgramacionService(db).crear(fundacion, data)


@router.get("/mis-programaciones", response_model=list[ProgramacionOut])
async def mis_programaciones(db: DbDep, fundacion: FundacionDep):
    return await ProgramacionService(db).listar(fundacion.id)


@router.post("/programaciones/{programacion_id}/autorizar", response_model=ProgramacionOut)
async def autorizar_programacion(db: DbDep, fundacion: FundacionDep, programacion_id: uuid.UUID):
    return await ProgramacionService(db).autorizar(programacion_id, fundacion)


@router.post("/programaciones/{programacion_id}/finalizar", response_model=ProgramacionOut)
async def finalizar_programacion(db: DbDep, fundacion: FundacionDep, programacion_id: uuid.UUID):
    return await ProgramacionService(db).finalizar(programacion_id, fundacion)


@router.post("/programaciones/{programacion_id}/imagenes", response_model=ProgramacionOut)
async def subir_imagen_programacion(
    db: DbDep,
    fundacion: FundacionDep,
    programacion_id: uuid.UUID,
    archivo: Annotated[UploadFile, File()],
):
    """Agrega una foto (máx. 8) que se copia a las convocatorias de la programación."""
    return await ProgramacionService(db).subir_imagen(programacion_id, fundacion, archivo)


@router.delete("/programaciones/{programacion_id}/imagenes", response_model=ProgramacionOut)
async def eliminar_imagen_programacion(
    db: DbDep,
    fundacion: FundacionDep,
    programacion_id: uuid.UUID,
    ruta: Annotated[str, Query(min_length=1, max_length=500)],
):
    """Quita una foto de la programación y de sus convocatorias que aún no empiezan."""
    return await ProgramacionService(db).eliminar_imagen(programacion_id, fundacion, ruta)
