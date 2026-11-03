"""Endpoints de perfil de dominio (voluntario / fundación)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbDep
from app.core.exceptions import NotFoundError
from app.models.usuario import ROL_FUNDACION, ROL_VOLUNTARIO
from app.schemas.perfil import (
    FundacionPerfilInput,
    FundacionPerfilOut,
    PerfilEstado,
    VoluntarioPerfilInput,
    VoluntarioPerfilOut,
)
from app.services.perfil_service import PerfilService

router = APIRouter(prefix="/perfil", tags=["perfil"])

# Constantes de rol disponibles por si se requieren en validaciones futuras.
_ROLES = (ROL_VOLUNTARIO, ROL_FUNDACION)


@router.get("/estado", response_model=PerfilEstado)
async def estado_perfil(db: DbDep, user: CurrentUser):
    completo = await PerfilService(db).estado(user)
    return PerfilEstado(rol=user.rol, perfil_completo=completo)


# ─────────────── Voluntario ───────────────

@router.get("/voluntario", response_model=VoluntarioPerfilOut)
async def obtener_perfil_voluntario(db: DbDep, user: CurrentUser):
    perfil = await PerfilService(db).obtener_voluntario(user)
    if perfil is None:
        raise NotFoundError("Aún no has completado tu perfil de voluntario.")
    return perfil


@router.put("/voluntario", response_model=VoluntarioPerfilOut)
async def guardar_perfil_voluntario(
    db: DbDep, user: CurrentUser, data: VoluntarioPerfilInput
):
    return await PerfilService(db).guardar_voluntario(user, data)


# ─────────────── Fundación ───────────────

@router.get("/fundacion", response_model=FundacionPerfilOut)
async def obtener_perfil_fundacion(db: DbDep, user: CurrentUser):
    perfil = await PerfilService(db).obtener_fundacion(user)
    if perfil is None:
        raise NotFoundError("Aún no has completado el perfil de tu fundación.")
    return perfil


@router.put("/fundacion", response_model=FundacionPerfilOut)
async def guardar_perfil_fundacion(
    db: DbDep, user: CurrentUser, data: FundacionPerfilInput
):
    return await PerfilService(db).guardar_fundacion(user, data)
