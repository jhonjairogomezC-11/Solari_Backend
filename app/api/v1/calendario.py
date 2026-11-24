"""Calendario de actividades, exportación .ics y ejecución manual de recordatorios."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import (
    DbDep,
    SettingsDep,
    get_fundacion_actual,
    get_voluntario_actual,
    require_roles,
)
from app.models.fundacion import Fundacion
from app.models.usuario import ROL_ADMIN
from app.models.voluntario import Voluntario
from app.schemas.calendario import EventoCalendario, RecordatoriosResultado
from app.services.calendario_service import CalendarioService
from app.services.recordatorio_service import RecordatorioService

router = APIRouter(tags=["calendario"])

VoluntarioDep = Annotated[Voluntario, Depends(get_voluntario_actual)]
FundacionDep = Annotated[Fundacion, Depends(get_fundacion_actual)]


def _frontend_base(url: str) -> str | None:
    partes = urlsplit(url)
    if not partes.scheme or not partes.netloc:
        return None
    return f"{partes.scheme}://{partes.netloc}"


@router.get("/voluntario/calendario", response_model=list[EventoCalendario])
async def calendario_voluntario(
    db: DbDep,
    voluntario: VoluntarioDep,
    desde: date | None = None,
    hasta: date | None = None,
    incluir_pendientes: Annotated[bool, Query()] = True,
):
    """Actividades del voluntario en el rango (por defecto, desde hoy).

    Las postulaciones pendientes, en revisión o en lista de espera se marcan con
    `confirmada=false` y no exponen la dirección exacta ni el enlace virtual.
    """
    return await CalendarioService(db).de_voluntario(
        voluntario, desde, hasta, incluir_pendientes
    )


@router.get("/voluntario/calendario.ics")
async def calendario_voluntario_ics(db: DbDep, settings: SettingsDep, voluntario: VoluntarioDep):
    """Archivo iCalendar con las actividades aceptadas del voluntario."""
    contenido = await CalendarioService(db).ics_de_voluntario(
        voluntario, _frontend_base(settings.frontend_reset_url)
    )
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="solari-calendario.ics"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/fundacion/calendario", response_model=list[EventoCalendario])
async def calendario_fundacion(
    db: DbDep,
    fundacion: FundacionDep,
    desde: date | None = None,
    hasta: date | None = None,
):
    """Convocatorias publicadas de la organización con el número de aceptados."""
    return await CalendarioService(db).de_fundacion(fundacion, desde, hasta)


@router.post(
    "/admin/recordatorios/ejecutar",
    response_model=RecordatoriosResultado,
    dependencies=[Depends(require_roles(ROL_ADMIN))],
)
async def ejecutar_recordatorios(db: DbDep):
    """Crea ya los recordatorios de las actividades que empiezan mañana."""
    return RecordatoriosResultado(creados=await RecordatorioService(db).ejecutar())
