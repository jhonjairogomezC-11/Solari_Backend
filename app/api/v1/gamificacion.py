"""Endpoints de gamificación: XP, logros, ranking e intereses (voluntarios)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbDep, get_voluntario_actual
from app.models.voluntario import Voluntario
from app.schemas.gamificacion import (
    InteresesInput,
    InteresOut,
    LogroEstadoOut,
    RankingResponse,
    ResumenGamificacion,
    TransaccionXpOut,
)
from app.services.gamificacion_service import GamificacionService

router = APIRouter(tags=["gamificacion"])

VoluntarioDep = Annotated[Voluntario, Depends(get_voluntario_actual)]


@router.get("/gamificacion/resumen", response_model=ResumenGamificacion)
async def resumen(db: DbDep, voluntario: VoluntarioDep):
    return await GamificacionService(db).resumen(voluntario)


@router.get("/gamificacion/logros", response_model=list[LogroEstadoOut])
async def logros(db: DbDep, voluntario: VoluntarioDep):
    return await GamificacionService(db).logros_con_estado(voluntario.id)


@router.get("/gamificacion/xp/historial", response_model=list[TransaccionXpOut])
async def historial_xp(db: DbDep, voluntario: VoluntarioDep):
    return await GamificacionService(db).historial_xp(voluntario.id)


@router.get("/ranking", response_model=RankingResponse)
async def ranking(db: DbDep, voluntario: VoluntarioDep):
    return await GamificacionService(db).ranking(voluntario.id)


# ─────────────── Intereses ───────────────

@router.get("/intereses", response_model=list[InteresOut])
async def catalogo_intereses(db: DbDep, voluntario: VoluntarioDep):
    return await GamificacionService(db).catalogo_intereses()


@router.get("/mis-intereses", response_model=list[int])
async def mis_intereses(db: DbDep, voluntario: VoluntarioDep):
    return await GamificacionService(db).intereses_de(voluntario.id)


@router.put("/mis-intereses", response_model=list[int])
async def guardar_intereses(db: DbDep, voluntario: VoluntarioDep, data: InteresesInput):
    return await GamificacionService(db).guardar_intereses(voluntario.id, data.interes_ids)
