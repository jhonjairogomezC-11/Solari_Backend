"""Autorización del acudiente para voluntarios menores de edad.

- Voluntario: consultar estado, guardar datos del acudiente, descargar el formato
  y subir la autorización firmada (almacenamiento privado).
- Administración: listar y aprobar o rechazar autorizaciones (con auditoría).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response

from app.api.deps import DbDep, get_voluntario_actual, require_roles
from app.models.usuario import ROL_ADMIN, Usuario
from app.models.voluntario import Voluntario
from app.schemas.menores import (
    AcudienteInput,
    AdminAutorizacionesPage,
    AutorizacionOut,
    ResolverAutorizacionInput,
)
from app.services.menores_service import MenoresService

router = APIRouter(tags=["menores"])

VoluntarioDep = Annotated[Voluntario, Depends(get_voluntario_actual)]
AdminDep = Annotated[Usuario, Depends(require_roles(ROL_ADMIN))]


# ─────────────── Voluntario ───────────────

@router.get("/perfil/voluntario/autorizacion", response_model=AutorizacionOut)
async def estado_autorizacion(vol: VoluntarioDep):
    return MenoresService.resumen(vol)


@router.put("/perfil/voluntario/acudiente", response_model=AutorizacionOut)
async def guardar_acudiente(db: DbDep, vol: VoluntarioDep, data: AcudienteInput):
    return await MenoresService(db).guardar_acudiente(vol, data)


@router.post("/perfil/voluntario/autorizacion", response_model=AutorizacionOut)
async def subir_autorizacion(
    db: DbDep, vol: VoluntarioDep, archivo: Annotated[UploadFile, File()]
):
    return await MenoresService(db).subir_autorizacion(vol, archivo)


@router.get("/perfil/voluntario/autorizacion/formato")
async def formato_autorizacion(db: DbDep, vol: VoluntarioDep):
    pdf = await MenoresService(db).formato_pdf(vol)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="autorizacion-acudiente-solari.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


# ─────────────── Administración ───────────────

@router.get("/admin/autorizaciones", response_model=AdminAutorizacionesPage)
async def listar_autorizaciones(
    db: DbDep,
    _: AdminDep,
    estado: Literal["PENDIENTE", "APROBADA", "RECHAZADA", "TODOS"] = "PENDIENTE",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
):
    filtro = None if estado == "TODOS" else estado
    return await MenoresService(db).listar(filtro, page, per_page)


@router.post("/admin/autorizaciones/{voluntario_id}/resolver", response_model=AutorizacionOut)
async def resolver_autorizacion(
    db: DbDep, admin: AdminDep, voluntario_id: uuid.UUID, data: ResolverAutorizacionInput
):
    return await MenoresService(db).resolver(admin, voluntario_id, data)
