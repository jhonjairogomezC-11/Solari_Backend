"""Perfil público de la organización, galería, verificación documental y reseñas."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.api.deps import (
    DbDep,
    OptionalUser,
    get_fundacion_actual,
    get_voluntario_actual,
)
from app.models.fundacion import Fundacion
from app.models.voluntario import Voluntario
from app.schemas.organizacion import (
    GaleriaItem,
    OrganizacionPublicaOut,
    PerfilPublicoUpdate,
    ResenaCreate,
    ResenaOut,
    ResenaRespuesta,
    ResenasPage,
    VerificacionEstadoOut,
)
from app.services.organizacion_service import OrganizacionService

router = APIRouter(tags=["organizaciones"])

FundacionDep = Annotated[Fundacion, Depends(get_fundacion_actual)]
VoluntarioDep = Annotated[Voluntario, Depends(get_voluntario_actual)]


# ─────────────── Público ───────────────

@router.get("/organizaciones/{fundacion_id}", response_model=OrganizacionPublicaOut)
async def perfil_publico(db: DbDep, usuario: OptionalUser, fundacion_id: uuid.UUID):
    return await OrganizacionService(db).perfil_publico(fundacion_id, usuario)


@router.get("/organizaciones/{fundacion_id}/resenas", response_model=ResenasPage)
async def listar_resenas(
    db: DbDep, fundacion_id: uuid.UUID,
    page: int = Query(1, ge=1), per_page: int = Query(10, ge=1, le=50),
):
    return await OrganizacionService(db).listar_resenas(fundacion_id, page, per_page)


# ─────────────── Reseñas ───────────────

@router.post(
    "/organizaciones/{fundacion_id}/resenas",
    response_model=ResenaOut,
    status_code=status.HTTP_201_CREATED,
)
async def crear_resena(
    db: DbDep, voluntario: VoluntarioDep, fundacion_id: uuid.UUID, data: ResenaCreate
):
    return await OrganizacionService(db).crear_resena(voluntario, fundacion_id, data)


@router.put("/resenas/{resena_id}/respuesta", response_model=ResenaOut)
async def responder_resena(
    db: DbDep, fundacion: FundacionDep, resena_id: uuid.UUID, data: ResenaRespuesta
):
    return await OrganizacionService(db).responder_resena(fundacion, resena_id, data.respuesta)


# ─────────────── Gestión del perfil público (organización) ───────────────

@router.put("/perfil/fundacion/publico", response_model=OrganizacionPublicaOut)
async def actualizar_perfil_publico(db: DbDep, fundacion: FundacionDep, data: PerfilPublicoUpdate):
    return await OrganizacionService(db).actualizar_perfil_publico(fundacion, data)


@router.post(
    "/perfil/fundacion/galeria", response_model=GaleriaItem, status_code=status.HTTP_201_CREATED
)
async def subir_galeria(
    db: DbDep,
    fundacion: FundacionDep,
    archivo: Annotated[UploadFile, File()],
    descripcion: Annotated[str | None, Form(max_length=200)] = None,
    contiene_menores: Annotated[bool, Form()] = False,
    autorizacion_imagen: Annotated[bool, Form()] = False,
):
    return await OrganizacionService(db).subir_galeria(
        fundacion, archivo, descripcion, contiene_menores, autorizacion_imagen
    )


@router.delete("/perfil/fundacion/galeria/{item_id}", status_code=204)
async def eliminar_galeria(db: DbDep, fundacion: FundacionDep, item_id: uuid.UUID):
    await OrganizacionService(db).eliminar_galeria(fundacion, item_id)


# ─────────────── Verificación documental (organización) ───────────────

@router.get("/perfil/fundacion/verificacion", response_model=VerificacionEstadoOut)
async def estado_verificacion(db: DbDep, fundacion: FundacionDep):
    return await OrganizacionService(db).estado_verificacion(fundacion)


@router.post("/perfil/fundacion/documentos", response_model=VerificacionEstadoOut)
async def subir_documento(
    db: DbDep,
    fundacion: FundacionDep,
    tipo_documento: Annotated[str, Form()],
    archivo: Annotated[UploadFile, File()],
):
    return await OrganizacionService(db).subir_documento(fundacion, tipo_documento, archivo)


@router.delete("/perfil/fundacion/documentos/{documento_id}", response_model=VerificacionEstadoOut)
async def eliminar_documento(db: DbDep, fundacion: FundacionDep, documento_id: uuid.UUID):
    return await OrganizacionService(db).eliminar_documento(fundacion, documento_id)


@router.post("/perfil/fundacion/verificacion/solicitar", response_model=VerificacionEstadoOut)
async def solicitar_verificacion(db: DbDep, fundacion: FundacionDep):
    return await OrganizacionService(db).solicitar_verificacion(fundacion)

