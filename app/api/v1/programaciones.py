"""Endpoints de actividades recurrentes (solo organizaciones)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

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
