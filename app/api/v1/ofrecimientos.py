"""Endpoints de objetos y servicios voluntarios."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.deps import (
    CurrentUser,
    DbDep,
    get_fundacion_actual,
    get_fundacion_opcional,
    get_voluntario_actual,
    get_voluntario_opcional,
)
from app.models.fundacion import Fundacion
from app.models.voluntario import Voluntario
from app.schemas.ofrecimiento import (
    CategoriasOfrecimiento,
    MensajeInput,
    MensajeOut,
    OfrecimientoCreate,
    OfrecimientoOut,
    OfrecimientoPage,
    OfrecimientoUpdate,
    ResponderSolicitud,
    SolicitudInteresCreate,
    SolicitudInteresOut,
)
from app.services.ofrecimiento_service import OfrecimientoService

router = APIRouter(tags=["ofrecimientos"])

VoluntarioDep = Annotated[Voluntario, Depends(get_voluntario_actual)]
FundacionDep = Annotated[Fundacion, Depends(get_fundacion_actual)]
VoluntarioOpt = Annotated[Voluntario | None, Depends(get_voluntario_opcional)]
FundacionOpt = Annotated[Fundacion | None, Depends(get_fundacion_opcional)]


@router.get("/ofrecimientos/categorias", response_model=CategoriasOfrecimiento)
async def categorias(_: CurrentUser):
    return OfrecimientoService.categorias()


# ─────────────── Exploración (cualquier usuario autenticado) ───────────────

@router.get("/ofrecimientos", response_model=OfrecimientoPage)
async def explorar(
    db: DbDep,
    _: CurrentUser,
    voluntario: VoluntarioOpt,
    fundacion: FundacionOpt,
    tipo: str | None = Query(default=None, pattern="^(OBJETO|SERVICIO)$"),
    categoria: str | None = Query(default=None, max_length=60),
    municipio_id: int | None = None,
    buscar: str | None = Query(default=None, max_length=120),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
):
    return await OfrecimientoService(db).explorar(
        tipo=tipo, categoria=categoria, municipio_id=municipio_id, buscar=buscar,
        page=page, per_page=per_page, voluntario_id=voluntario.id if voluntario else None,
        fundacion_id=fundacion.id if fundacion else None,
    )


@router.get("/mis-ofrecimientos", response_model=list[OfrecimientoOut])
async def mis_ofrecimientos(db: DbDep, voluntario: VoluntarioDep):
    return await OfrecimientoService(db).mis_ofrecimientos(voluntario)


@router.get("/ofrecimientos/{ofrecimiento_id}", response_model=OfrecimientoOut)
async def detalle(
    db: DbDep,
    _: CurrentUser,
    voluntario: VoluntarioOpt,
    fundacion: FundacionOpt,
    ofrecimiento_id: uuid.UUID,
):
    return await OfrecimientoService(db).detalle(
        ofrecimiento_id,
        voluntario.id if voluntario else None,
        fundacion.id if fundacion else None,
    )


# ─────────────── Voluntario: publicar y gestionar ───────────────

@router.post("/ofrecimientos", response_model=OfrecimientoOut, status_code=status.HTTP_201_CREATED)
async def crear(db: DbDep, voluntario: VoluntarioDep, data: OfrecimientoCreate):
    return await OfrecimientoService(db).crear(voluntario, data)


@router.put("/ofrecimientos/{ofrecimiento_id}", response_model=OfrecimientoOut)
async def actualizar(
    db: DbDep, voluntario: VoluntarioDep, ofrecimiento_id: uuid.UUID, data: OfrecimientoUpdate
):
    return await OfrecimientoService(db).actualizar(voluntario, ofrecimiento_id, data)


@router.post("/ofrecimientos/{ofrecimiento_id}/pausar", response_model=OfrecimientoOut)
async def pausar(db: DbDep, voluntario: VoluntarioDep, ofrecimiento_id: uuid.UUID):
    return await OfrecimientoService(db).cambiar_estado(voluntario, ofrecimiento_id, "PAUSAR")


@router.post("/ofrecimientos/{ofrecimiento_id}/reanudar", response_model=OfrecimientoOut)
async def reanudar(db: DbDep, voluntario: VoluntarioDep, ofrecimiento_id: uuid.UUID):
    return await OfrecimientoService(db).cambiar_estado(voluntario, ofrecimiento_id, "REANUDAR")


@router.post("/ofrecimientos/{ofrecimiento_id}/finalizar", response_model=OfrecimientoOut)
async def finalizar(db: DbDep, voluntario: VoluntarioDep, ofrecimiento_id: uuid.UUID):
    return await OfrecimientoService(db).cambiar_estado(voluntario, ofrecimiento_id, "FINALIZAR")


@router.post("/ofrecimientos/{ofrecimiento_id}/imagenes", response_model=OfrecimientoOut)
async def subir_imagen(
    db: DbDep,
    voluntario: VoluntarioDep,
    ofrecimiento_id: uuid.UUID,
    archivo: Annotated[UploadFile, File()],
):
    return await OfrecimientoService(db).subir_imagen(voluntario, ofrecimiento_id, archivo)


# ─────────────── Organización: "Me interesa" ───────────────

@router.post(
    "/ofrecimientos/{ofrecimiento_id}/me-interesa",
    response_model=SolicitudInteresOut,
    status_code=status.HTTP_201_CREATED,
)
async def me_interesa(
    db: DbDep, fundacion: FundacionDep, ofrecimiento_id: uuid.UUID, data: SolicitudInteresCreate
):
    return await OfrecimientoService(db).solicitar(fundacion, ofrecimiento_id, data)


# ─────────────── Solicitudes (ambas partes) ───────────────

@router.get("/solicitudes-interes", response_model=list[SolicitudInteresOut])
async def mis_solicitudes(db: DbDep, user: CurrentUser):
    return await OfrecimientoService(db).mis_solicitudes(user)


@router.put("/solicitudes-interes/{solicitud_id}/responder", response_model=SolicitudInteresOut)
async def responder(db: DbDep, user: CurrentUser, solicitud_id: uuid.UUID, data: ResponderSolicitud):
    return await OfrecimientoService(db).responder(user, solicitud_id, data.decision)


@router.post("/solicitudes-interes/{solicitud_id}/confirmar", response_model=SolicitudInteresOut)
async def confirmar(db: DbDep, user: CurrentUser, solicitud_id: uuid.UUID):
    return await OfrecimientoService(db).confirmar(user, solicitud_id)


@router.post("/solicitudes-interes/{solicitud_id}/cancelar", response_model=SolicitudInteresOut)
async def cancelar(db: DbDep, user: CurrentUser, solicitud_id: uuid.UUID):
    return await OfrecimientoService(db).cancelar(user, solicitud_id)


@router.get("/solicitudes-interes/{solicitud_id}/mensajes", response_model=list[MensajeOut])
async def mensajes(db: DbDep, user: CurrentUser, solicitud_id: uuid.UUID):
    return await OfrecimientoService(db).mensajes(user, solicitud_id)


@router.post("/solicitudes-interes/{solicitud_id}/mensajes", response_model=list[MensajeOut])
async def enviar_mensaje(
    db: DbDep, user: CurrentUser, solicitud_id: uuid.UUID, data: MensajeInput
):
    return await OfrecimientoService(db).enviar_mensaje(user, solicitud_id, data)
