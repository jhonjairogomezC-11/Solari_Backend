"""Pruebas unitarias (sin base de datos) del calendario, el .ics y los recordatorios."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.tareas import recordatorios_activos
from app.services.calendario_service import (
    EventoIcs,
    escapar_ics,
    generar_ics,
    hoy_bogota,
    plegar_linea,
    resolver_rango,
    uid_postulacion,
)
from app.services.programacion_service import (
    imagenes_de_plantilla,
    plantilla_sin_imagenes,
)
from app.services.recordatorio_service import fecha_recordatorio, mensaje_recordatorio

_AHORA = datetime(2025, 3, 10, 15, 0, tzinfo=UTC)


def _desplegar(ics: str) -> list[str]:
    """Une las líneas plegadas (RFC 5545 §3.1) para inspeccionar propiedades."""
    return ics.replace("\r\n ", "").split("\r\n")


# ── Escape y plegado ──


def test_escapar_ics_caracteres_especiales():
    assert escapar_ics("a,b;c\\d\ne") == "a\\,b\\;c\\\\d\\ne"
    assert escapar_ics("x\r\ny\rz") == "x\\ny\\nz"
    assert escapar_ics(None) == ""


def test_plegar_linea_respeta_75_octetos_y_utf8():
    linea = "SUMMARY:" + "ñ" * 100
    plegada = plegar_linea(linea)
    partes = plegada.split("\r\n")
    assert len(partes) > 1
    assert all(len(p.encode("utf-8")) <= 75 for p in partes)
    assert all(p.startswith(" ") for p in partes[1:])
    assert "".join([partes[0], *(p[1:] for p in partes[1:])]) == linea


def test_plegar_linea_corta_no_cambia():
    assert plegar_linea("VERSION:2.0") == "VERSION:2.0"


# ── Generación del .ics ──


def test_generar_ics_estructura_crlf_y_uid():
    pid = uuid.uuid4()
    ev = EventoIcs(
        uid=uid_postulacion(pid),
        titulo="Jornada de limpieza, parque; norte",
        fecha_inicio=date(2025, 3, 15),
        fecha_fin=date(2025, 3, 15),
        hora_inicio=time(8, 0),
        hora_fin=time(12, 30),
        descripcion="Lleva agua\ny gorra",
        ubicacion="Calle 1 # 2-3, Bogotá",
        url="https://solari.co/app/convocatorias/abc",
        organizacion="Fundación Sol",
    )
    ics = generar_ics([ev], ahora=_AHORA)
    assert ics.startswith("BEGIN:VCALENDAR\r\n")
    assert ics.endswith("END:VCALENDAR\r\n")
    # Todos los saltos son CRLF.
    assert "\n" not in ics.replace("\r\n", "")
    lineas = _desplegar(ics)
    assert "VERSION:2.0" in lineas
    assert f"UID:postulacion-{pid}@solari.co" in lineas
    assert "DTSTAMP:20250310T150000Z" in lineas
    # 08:00 en Bogotá (UTC-5) = 13:00 UTC.
    assert "DTSTART:20250315T130000Z" in lineas
    assert "DTEND:20250315T173000Z" in lineas
    assert "SUMMARY:Jornada de limpieza\\, parque\\; norte" in lineas
    assert "LOCATION:Calle 1 # 2-3\\, Bogotá" in lineas
    assert "DESCRIPTION:Organización: Fundación Sol\\nLleva agua\\ny gorra" in lineas
    assert lineas.count("BEGIN:VEVENT") == 1 and lineas.count("END:VEVENT") == 1


def test_generar_ics_dia_completo_dtend_exclusivo():
    ev = EventoIcs(
        uid="u1@solari.co",
        titulo="Campamento",
        fecha_inicio=date(2025, 12, 30),
        fecha_fin=date(2025, 12, 31),
    )
    lineas = _desplegar(generar_ics([ev], ahora=_AHORA))
    assert "DTSTART;VALUE=DATE:20251230" in lineas
    assert "DTEND;VALUE=DATE:20260101" in lineas


def test_generar_ics_sin_hora_fin_dura_una_hora():
    ev = EventoIcs(
        uid="u2@solari.co",
        titulo="Taller",
        fecha_inicio=date(2025, 3, 15),
        fecha_fin=date(2025, 3, 15),
        hora_inicio=time(20, 0),
    )
    lineas = _desplegar(generar_ics([ev], ahora=_AHORA))
    # 20:00 Bogotá = 01:00 UTC del día siguiente.
    assert "DTSTART:20250316T010000Z" in lineas
    assert "DTEND:20250316T020000Z" in lineas


def test_generar_ics_vacio_es_valido():
    lineas = _desplegar(generar_ics([], ahora=_AHORA))
    assert lineas[0] == "BEGIN:VCALENDAR"
    assert "BEGIN:VEVENT" not in lineas


def test_url_sin_saltos_de_linea():
    ev = EventoIcs(
        uid="u3@solari.co",
        titulo="X",
        fecha_inicio=date(2025, 3, 15),
        fecha_fin=date(2025, 3, 15),
        url="https://a.co/x\r\nBEGIN:VEVENT",
    )
    lineas = _desplegar(generar_ics([ev], ahora=_AHORA))
    assert lineas.count("BEGIN:VEVENT") == 1


# ── Fechas en Bogotá y ventana de recordatorios ──


def test_hoy_bogota_cruce_de_medianoche_utc():
    # 03:00 UTC del 10 de marzo = 22:00 del 9 de marzo en Bogotá.
    assert hoy_bogota(datetime(2025, 3, 10, 3, 0, tzinfo=UTC)) == date(2025, 3, 9)
    assert hoy_bogota(datetime(2025, 3, 10, 5, 0, tzinfo=UTC)) == date(2025, 3, 10)


def test_fecha_recordatorio_es_manana_en_bogota():
    assert fecha_recordatorio(datetime(2025, 3, 10, 3, 0, tzinfo=UTC)) == date(2025, 3, 10)
    assert fecha_recordatorio(datetime(2025, 3, 10, 12, 0, tzinfo=UTC)) == date(2025, 3, 11)
    # Fin de año.
    assert fecha_recordatorio(datetime(2025, 12, 31, 18, 0, tzinfo=UTC)) == date(2026, 1, 1)


def test_fecha_recordatorio_acepta_datetime_ingenuo_como_utc():
    assert fecha_recordatorio(datetime(2025, 3, 10, 3, 0)) == date(2025, 3, 10)


def test_mensaje_recordatorio():
    msg = mensaje_recordatorio("Limpieza", "Fundación Sol", date(2025, 3, 11), time(8, 30))
    assert "11/03/2025" in msg and "08:30" in msg and "«Limpieza»" in msg
    assert "a las" not in mensaje_recordatorio("L", "F", date(2025, 3, 11))


# ── Rango del calendario ──


def test_resolver_rango_por_defecto_y_validaciones():
    hoy = date(2025, 3, 10)
    desde, hasta = resolver_rango(None, None, hoy)
    assert desde == hoy and hasta > hoy
    with pytest.raises(AppError):
        resolver_rango(date(2025, 3, 10), date(2025, 3, 1), hoy)
    with pytest.raises(AppError):
        resolver_rango(date(2025, 1, 1), date(2027, 1, 1), hoy)


# ── Tarea de fondo ──


def _settings(**kw) -> Settings:
    return Settings(jwt_secret="secreto-de-prueba-suficientemente-largo-123", **kw)  # type: ignore[call-arg]


def test_recordatorios_desactivados_en_testing_y_ci():
    assert recordatorios_activos(_settings(app_env="local")) is True
    assert recordatorios_activos(_settings(app_env="testing")) is False
    assert recordatorios_activos(_settings(app_env="CI")) is False
    assert recordatorios_activos(_settings(app_env="local", reminders_enabled=False)) is False


# ── Fotos de programaciones ──


def test_imagenes_de_plantilla():
    assert imagenes_de_plantilla(None) == []
    assert imagenes_de_plantilla({"imagenes": "x"}) == []
    assert imagenes_de_plantilla({"imagenes": ["a", 3, "", "b"]}) == ["a", "b"]
    assert plantilla_sin_imagenes({"titulo": "T", "imagenes": ["a"]}) == {"titulo": "T"}
