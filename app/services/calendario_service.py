"""Calendario de actividades (voluntario y organización) y exportación iCalendar.

Las fechas y horas de las convocatorias están en hora local de Bogotá. Colombia no
usa horario de verano, así que se usa un desfase fijo UTC-5 (sin depender de la
base de datos de zonas horarias del sistema operativo).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.fundacion import Fundacion
from app.models.postulacion import (
    ESTADO_ACEPTADO,
    ESTADO_EN_REVISION,
    ESTADO_LISTA_ESPERA,
    ESTADO_PENDIENTE,
)
from app.models.voluntario import Voluntario
from app.repositories.calendario_repo import CalendarioRepository
from app.schemas.calendario import EventoCalendario

BOGOTA = timezone(timedelta(hours=-5), "America/Bogota")

ESTADOS_EN_ESPERA = (ESTADO_PENDIENTE, ESTADO_EN_REVISION, ESTADO_LISTA_ESPERA)

# Rango por defecto y máximo de una consulta de calendario.
DIAS_POR_DEFECTO = 180
DIAS_MAXIMO = 400
# El .ics incluye actividades que terminaron hace poco (para no borrarlas de golpe).
ICS_DIAS_ATRAS = 30

_PRODID = "-//Solari//Calendario de voluntariado//ES"


def hoy_bogota(ahora: datetime | None = None) -> date:
    """Fecha local de Bogotá para un instante (por defecto, ahora)."""
    ahora = ahora or datetime.now(UTC)
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=UTC)
    return ahora.astimezone(BOGOTA).date()


def resolver_rango(desde: date | None, hasta: date | None, hoy: date) -> tuple[date, date]:
    """Completa y valida el rango [desde, hasta] de una consulta de calendario."""
    inicio = desde or hoy
    fin = hasta or (inicio + timedelta(days=DIAS_POR_DEFECTO))
    if fin < inicio:
        raise AppError("La fecha 'hasta' debe ser mayor o igual a 'desde'.", 422)
    if (fin - inicio).days > DIAS_MAXIMO:
        raise AppError(f"El rango no puede superar {DIAS_MAXIMO} días.", 422)
    return inicio, fin


# ─────────────── iCalendar (RFC 5545) ───────────────


def escapar_ics(valor: str | None) -> str:
    """Escapa un valor TEXT: barra invertida, punto y coma, coma y saltos de línea."""
    if not valor:
        return ""
    return (
        valor.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\r", "\\n")
        .replace("\n", "\\n")
    )


def plegar_linea(linea: str) -> str:
    """Pliega una línea de contenido a 75 octetos (RFC 5545 §3.1).

    Las continuaciones empiezan con un espacio. Nunca parte un carácter UTF-8.
    """
    partes: list[str] = []
    actual = ""
    tam = 0
    limite = 75
    for ch in linea:
        n = len(ch.encode("utf-8"))
        if tam + n > limite:
            partes.append(actual)
            actual = " "
            tam = 1  # el espacio inicial cuenta
        actual += ch
        tam += n
    partes.append(actual)
    return "\r\n".join(partes)


def _fmt_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class EventoIcs:
    uid: str
    titulo: str
    fecha_inicio: date
    fecha_fin: date
    hora_inicio: time | None = None
    hora_fin: time | None = None
    descripcion: str | None = None
    ubicacion: str | None = None
    url: str | None = None
    organizacion: str | None = None


def _lineas_evento(ev: EventoIcs, dtstamp: str) -> list[str]:
    lineas = ["BEGIN:VEVENT", f"UID:{ev.uid}", f"DTSTAMP:{dtstamp}"]
    if ev.hora_inicio is None:
        # Evento de día completo: DTEND es exclusivo (día siguiente al último).
        lineas.append(f"DTSTART;VALUE=DATE:{ev.fecha_inicio:%Y%m%d}")
        lineas.append(f"DTEND;VALUE=DATE:{ev.fecha_fin + timedelta(days=1):%Y%m%d}")
    else:
        inicio = datetime.combine(ev.fecha_inicio, ev.hora_inicio, BOGOTA)
        if ev.hora_fin is not None:
            fin = datetime.combine(ev.fecha_fin, ev.hora_fin, BOGOTA)
        else:
            fin = datetime.combine(ev.fecha_fin, ev.hora_inicio, BOGOTA) + timedelta(hours=1)
        if fin <= inicio:
            fin = inicio + timedelta(hours=1)
        lineas.append(f"DTSTART:{_fmt_utc(inicio)}")
        lineas.append(f"DTEND:{_fmt_utc(fin)}")
    lineas.append(f"SUMMARY:{escapar_ics(ev.titulo)}")
    descripcion = ev.descripcion or ""
    if ev.organizacion:
        descripcion = f"Organización: {ev.organizacion}\n{descripcion}".strip()
    if descripcion:
        lineas.append(f"DESCRIPTION:{escapar_ics(descripcion)}")
    if ev.ubicacion:
        lineas.append(f"LOCATION:{escapar_ics(ev.ubicacion)}")
    if ev.url:
        # URL es de tipo URI: no se escapa como TEXT, pero no puede tener saltos.
        lineas.append(f"URL:{ev.url.replace(chr(13), '').replace(chr(10), '')}")
    lineas.append("STATUS:CONFIRMED")
    lineas.append("END:VEVENT")
    return lineas


def generar_ics(
    eventos: Iterable[EventoIcs], ahora: datetime | None = None, nombre: str = "Solari"
) -> str:
    """Construye un archivo iCalendar completo con finales de línea CRLF."""
    dtstamp = _fmt_utc(ahora or datetime.now(UTC))
    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{_PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escapar_ics(nombre)}",
        "X-WR-TIMEZONE:America/Bogota",
    ]
    for ev in eventos:
        lineas.extend(_lineas_evento(ev, dtstamp))
    lineas.append("END:VCALENDAR")
    return "".join(plegar_linea(linea) + "\r\n" for linea in lineas)


def uid_postulacion(postulacion_id: uuid.UUID) -> str:
    return f"postulacion-{postulacion_id}@solari.co"


def _ubicacion(modalidad: str, direccion: str | None, municipio: str | None) -> str | None:
    if modalidad == "VIRTUAL":
        return "Virtual"
    partes = [p for p in (direccion, municipio) if p]
    return ", ".join(partes) or None


# ─────────────── Servicio ───────────────


class CalendarioService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CalendarioRepository(db)

    async def de_voluntario(
        self,
        voluntario: Voluntario,
        desde: date | None,
        hasta: date | None,
        incluir_pendientes: bool = True,
    ) -> list[EventoCalendario]:
        inicio, fin = resolver_rango(desde, hasta, hoy_bogota())
        estados = [ESTADO_ACEPTADO]
        if incluir_pendientes:
            estados.extend(ESTADOS_EN_ESPERA)
        filas = await self.repo.actividades_voluntario(voluntario.id, estados, inicio, fin)
        salida: list[EventoCalendario] = []
        for post, pub, org, municipio in filas:
            aceptada = post.estado == ESTADO_ACEPTADO
            salida.append(
                EventoCalendario(
                    publicacion_id=pub.id,
                    postulacion_id=post.id,
                    estado_postulacion=post.estado,
                    confirmada=aceptada,
                    titulo=pub.titulo,
                    fecha_inicio=pub.fecha_inicio,
                    fecha_fin=pub.fecha_fin,
                    hora_inicio=pub.hora_inicio,
                    hora_fin=pub.hora_fin,
                    modalidad=pub.modalidad,
                    municipio=municipio,
                    direccion_exacta=pub.direccion_exacta if aceptada else None,
                    enlace_virtual=pub.enlace_virtual if aceptada else None,
                    horas_reconocidas=pub.horas_reconocidas or 0,
                    organizacion_id=pub.fundacion_id,
                    organizacion=org,
                )
            )
        return salida

    async def ics_de_voluntario(self, voluntario: Voluntario, frontend_base: str | None) -> str:
        desde = hoy_bogota() - timedelta(days=ICS_DIAS_ATRAS)
        filas = await self.repo.actividades_voluntario(
            voluntario.id, [ESTADO_ACEPTADO], desde, None
        )
        eventos = []
        for post, pub, org, municipio in filas:
            url = f"{frontend_base.rstrip('/')}/app/convocatorias/{pub.id}" if frontend_base else None
            detalle = []
            if pub.enlace_virtual:
                detalle.append(f"Enlace: {pub.enlace_virtual}")
            if pub.horas_reconocidas:
                detalle.append(f"Horas reconocidas: {pub.horas_reconocidas}")
            eventos.append(
                EventoIcs(
                    uid=uid_postulacion(post.id),
                    titulo=pub.titulo,
                    fecha_inicio=pub.fecha_inicio,
                    fecha_fin=pub.fecha_fin,
                    hora_inicio=pub.hora_inicio,
                    hora_fin=pub.hora_fin,
                    descripcion="\n".join(detalle) or None,
                    ubicacion=_ubicacion(pub.modalidad, pub.direccion_exacta, municipio),
                    url=url,
                    organizacion=org,
                )
            )
        return generar_ics(eventos, nombre="Solari · Mis actividades")

    async def de_fundacion(
        self, fundacion: Fundacion, desde: date | None, hasta: date | None
    ) -> list[EventoCalendario]:
        inicio, fin = resolver_rango(desde, hasta, hoy_bogota())
        filas = await self.repo.actividades_fundacion(fundacion.id, inicio, fin)
        return [
            EventoCalendario(
                publicacion_id=pub.id,
                titulo=pub.titulo,
                fecha_inicio=pub.fecha_inicio,
                fecha_fin=pub.fecha_fin,
                hora_inicio=pub.hora_inicio,
                hora_fin=pub.hora_fin,
                modalidad=pub.modalidad,
                municipio=municipio,
                direccion_exacta=pub.direccion_exacta,
                enlace_virtual=pub.enlace_virtual,
                horas_reconocidas=pub.horas_reconocidas or 0,
                organizacion_id=pub.fundacion_id,
                organizacion=org,
                cupo_maximo=pub.cupo_maximo,
                voluntarios_aceptados=int(aceptados or 0),
            )
            for pub, org, municipio, aceptados in filas
        ]
