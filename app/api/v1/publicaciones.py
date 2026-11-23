"""Endpoints de convocatorias (publicaciones)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status

from app.api.deps import DbDep, get_fundacion_actual, get_voluntario_opcional
from app.core.rate_limit import limiter
from app.models.fundacion import Fundacion
from app.models.voluntario import Voluntario
from app.schemas.publicacion import (
    PaginatedResponse,
    PublicacionCreate,
    PublicacionOut,
    PublicacionUpdate,
)
from app.services.publicacion_service import PublicacionService

router = APIRouter(tags=["convocatorias"])

FundacionDep = Annotated[Fundacion, Depends(get_fundacion_actual)]
VoluntarioOpt = Annotated[Voluntario | None, Depends(get_voluntario_opcional)]


# ─────────────── Público ───────────────

@router.get("/publicaciones", response_model=PaginatedResponse[PublicacionOut])
async def listar_publicaciones(
    db: DbDep,
    voluntario: VoluntarioOpt,
    categoria_id: int | None = None,
    modalidad: str | None = None,
    municipio_id: int | None = None,
    buscar: str | None = Query(default=None, max_length=120),
    page: int = Query(1, ge=1),
    per_page: int = Query(15, ge=1, le=50),
):
    return await PublicacionService(db).listar_publicas(
        categoria_id=categoria_id,
        modalidad=modalidad,
        municipio_id=municipio_id,
        buscar=buscar,
        voluntario_id=voluntario.id if voluntario else None,
        page=page,
        per_page=per_page,
    )


@router.get("/publicaciones/{publicacion_id}", response_model=PublicacionOut)
async def detalle_publicacion(db: DbDep, voluntario: VoluntarioOpt, publicacion_id: uuid.UUID):
    return await PublicacionService(db).obtener_publica(
        publicacion_id, voluntario.id if voluntario else None
    )


# ─────────────── Fundación ───────────────

@router.get("/mis-publicaciones", response_model=PaginatedResponse[PublicacionOut])
async def mis_publicaciones(
    db: DbDep,
    fundacion: FundacionDep,
    page: int = Query(1, ge=1),
    per_page: int = Query(15, ge=1, le=50),
):
    return await PublicacionService(db).mis_publicaciones(fundacion.id, page, per_page)


@router.get("/mis-publicaciones/{publicacion_id}", response_model=PublicacionOut)
async def mi_publicacion(db: DbDep, fundacion: FundacionDep, publicacion_id: uuid.UUID):
    return await PublicacionService(db).obtener_propia(publicacion_id, fundacion.id)


@router.post("/publicaciones", response_model=PublicacionOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def crear_publicacion(
    request: Request,
    db: DbDep,
    fundacion: FundacionDep,
    data: PublicacionCreate,
):
    return await PublicacionService(db).crear(fundacion.id, data)


@router.put("/publicaciones/{publicacion_id}", response_model=PublicacionOut)
async def actualizar_publicacion(
    db: DbDep,
    fundacion: FundacionDep,
    publicacion_id: uuid.UUID,
    data: PublicacionUpdate,
):
    return await PublicacionService(db).actualizar(publicacion_id, fundacion.id, data)


@router.post("/publicaciones/{publicacion_id}/imagenes", response_model=PublicacionOut)
async def subir_imagen_publicacion(
    db: DbDep,
    fundacion: FundacionDep,
    publicacion_id: uuid.UUID,
    archivo: Annotated[UploadFile, File()],
):
    return await PublicacionService(db).subir_imagen(publicacion_id, fundacion.id, archivo)


@router.delete(
    "/publicaciones/{publicacion_id}/imagenes/{imagen_id}", response_model=PublicacionOut
)
async def eliminar_imagen_publicacion(
    db: DbDep, fundacion: FundacionDep, publicacion_id: uuid.UUID, imagen_id: uuid.UUID
):
    return await PublicacionService(db).eliminar_imagen(publicacion_id, fundacion.id, imagen_id)


@router.post("/publicaciones/{publicacion_id}/publicar", response_model=PublicacionOut)
async def publicar_publicacion(
    db: DbDep, fundacion: FundacionDep, publicacion_id: uuid.UUID
):
    return await PublicacionService(db).publicar(publicacion_id, fundacion.id)


@router.post("/publicaciones/{publicacion_id}/cancelar", response_model=PublicacionOut)
async def cancelar_publicacion(
    db: DbDep, fundacion: FundacionDep, publicacion_id: uuid.UUID
):
    return await PublicacionService(db).cancelar(publicacion_id, fundacion.id)
