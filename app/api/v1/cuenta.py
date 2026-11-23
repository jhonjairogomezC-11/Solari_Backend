"""Endpoints de cuenta: preferencias de notificación, trayectoria y recomendaciones."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbDep, get_voluntario_actual
from app.models.voluntario import Voluntario
from app.schemas.cuenta import (
    PreferenciasInput,
    PreferenciasOut,
    TrayectoriaOut,
)
from app.schemas.publicacion import PublicacionOut
from app.services.cuenta_service import CuentaService
from app.services.publicacion_service import PublicacionService
from app.services.recomendacion_service import RecomendacionService

router = APIRouter(tags=["cuenta"])

VoluntarioDep = Annotated[Voluntario, Depends(get_voluntario_actual)]


# ── Preferencias de notificación (cualquier usuario) ──

@router.get("/cuenta/preferencias-notificacion", response_model=PreferenciasOut)
async def obtener_preferencias(db: DbDep, user: CurrentUser):
    return await CuentaService(db).preferencias(user.id)


@router.put("/cuenta/preferencias-notificacion", response_model=PreferenciasOut)
async def guardar_preferencias(db: DbDep, user: CurrentUser, data: PreferenciasInput):
    return await CuentaService(db).guardar_preferencias(user.id, data.model_dump())


# ── Trayectoria del voluntario ──

@router.get("/voluntario/trayectoria", response_model=TrayectoriaOut)
async def trayectoria(db: DbDep, voluntario: VoluntarioDep):
    return await CuentaService(db).trayectoria(voluntario)


# ── Recomendaciones personalizadas ──

@router.get("/voluntario/recomendaciones", response_model=list[PublicacionOut])
async def recomendaciones(db: DbDep, voluntario: VoluntarioDep):
    pares = await RecomendacionService(db).recomendar(voluntario)
    # Enriquecido con la organización y el porcentaje de coincidencia de habilidades.
    return await PublicacionService(db)._enriquecer([p for p, _ in pares], voluntario.id)
