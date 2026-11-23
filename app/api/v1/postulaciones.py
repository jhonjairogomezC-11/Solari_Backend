"""Endpoints de postulaciones."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Request, status

from app.api.deps import CurrentUser, DbDep, get_fundacion_actual, get_voluntario_actual
from app.core.rate_limit import limiter
from app.models.fundacion import Fundacion
from app.models.voluntario import Voluntario
from app.schemas.postulacion import (
    ConfirmarAsistencia,
    HistorialOut,
    PaginatedResponse,
    PostulacionCreate,
    PostulacionOut,
    PostulacionResponder,
    PostulantesPage,
    RetirarInput,
)
from app.services.postulacion_service import PostulacionService

router = APIRouter(tags=["postulaciones"])

VoluntarioDep = Annotated[Voluntario, Depends(get_voluntario_actual)]
FundacionDep = Annotated[Fundacion, Depends(get_fundacion_actual)]


# ─────────────── Voluntario ───────────────

@router.post("/postulaciones", response_model=PostulacionOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def postular(
    request: Request,
    db: DbDep,
    voluntario: VoluntarioDep,
    data: PostulacionCreate,
):
    return await PostulacionService(db).postular(voluntario, data)


@router.get("/mis-postulaciones", response_model=PaginatedResponse[PostulacionOut])
async def mis_postulaciones(
    db: DbDep,
    voluntario: VoluntarioDep,
    page: int = Query(1, ge=1),
    per_page: int = Query(15, ge=1, le=50),
):
    return await PostulacionService(db).mis_postulaciones(voluntario.id, page, per_page)


@router.post("/postulaciones/{postulacion_id}/retirar", response_model=PostulacionOut)
async def retirar(
    db: DbDep,
    voluntario: VoluntarioDep,
    postulacion_id: uuid.UUID,
    data: Annotated[RetirarInput | None, Body()] = None,
):
    data = data or RetirarInput()
    return await PostulacionService(db).retirar(
        postulacion_id, voluntario, data.confirmar, data.motivo
    )


@router.get("/postulaciones/{postulacion_id}/historial", response_model=list[HistorialOut])
async def historial(db: DbDep, user: CurrentUser, postulacion_id: uuid.UUID):
    return await PostulacionService(db).historial(postulacion_id, user)


# ─────────────── Fundación ───────────────

@router.get(
    "/publicaciones/{publicacion_id}/postulaciones",
    response_model=PostulantesPage,
)
async def postulaciones_de_publicacion(
    db: DbDep,
    fundacion: FundacionDep,
    publicacion_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(15, ge=1, le=50),
):
    return await PostulacionService(db).de_publicacion(
        publicacion_id, fundacion.id, page, per_page
    )


@router.put("/postulaciones/{postulacion_id}/responder", response_model=PostulacionOut)
async def responder(
    db: DbDep,
    fundacion: FundacionDep,
    postulacion_id: uuid.UUID,
    data: PostulacionResponder,
):
    return await PostulacionService(db).responder(postulacion_id, fundacion, data)


@router.post(
    "/postulaciones/{postulacion_id}/confirmar-asistencia", response_model=PostulacionOut
)
async def confirmar_asistencia(
    db: DbDep,
    fundacion: FundacionDep,
    postulacion_id: uuid.UUID,
    data: ConfirmarAsistencia,
):
    return await PostulacionService(db).confirmar_asistencia(postulacion_id, fundacion, data)
