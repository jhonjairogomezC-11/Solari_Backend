"""Pruebas sin base de datos de la autorización del acudiente para menores."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.core.exceptions import ConflictError
from app.schemas.menores import AcudienteInput, ResolverAutorizacionInput
from app.services import menores_service as ms

HOY = date(2026, 6, 15)


# ─────────────── Edad ───────────────

@pytest.mark.parametrize(
    ("nacimiento", "hoy", "esperada"),
    [
        (date(2008, 6, 15), HOY, 18),  # cumple hoy
        (date(2008, 6, 16), HOY, 17),  # cumple mañana
        (date(2008, 6, 14), HOY, 18),  # cumplió ayer
        (date(2008, 12, 31), HOY, 17),
        (date(2008, 1, 1), HOY, 18),
        (date(2026, 6, 15), HOY, 0),
        # 29 de febrero: en año no bisiesto los cumple el 1 de marzo.
        (date(2008, 2, 29), date(2026, 2, 28), 17),
        (date(2008, 2, 29), date(2026, 3, 1), 18),
        (date(2008, 2, 29), date(2028, 2, 29), 20),
    ],
)
def test_calcular_edad(nacimiento: date, hoy: date, esperada: int) -> None:
    assert ms.calcular_edad(nacimiento, hoy) == esperada


def test_es_menor_en_el_borde_de_los_18() -> None:
    assert ms.es_menor(date(2008, 6, 16), HOY) is True
    assert ms.es_menor(date(2008, 6, 15), HOY) is False
    assert ms.es_menor(None, HOY) is False


def test_hoy_bogota_usa_utc_menos_5(monkeypatch: pytest.MonkeyPatch) -> None:
    # 2026-06-16 03:00 UTC sigue siendo 15 de junio en Bogotá.
    class _Fijo(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return datetime(2026, 6, 16, 3, 0, tzinfo=UTC).astimezone(tz)

    import app.core.edad as edad

    monkeypatch.setattr(edad, "datetime", _Fijo)
    assert ms.hoy_bogota() == date(2026, 6, 15)


# ─────────────── Estado y regla de aceptación ───────────────

def test_estado_autorizacion() -> None:
    adulto, menor = date(2000, 1, 1), date(2012, 1, 1)
    assert ms.estado_autorizacion(adulto, None, HOY) == ms.AUT_NO_REQUERIDA
    assert ms.estado_autorizacion(adulto, ms.AUT_RECHAZADA, HOY) == ms.AUT_NO_REQUERIDA
    assert ms.estado_autorizacion(menor, None, HOY) is None
    assert ms.estado_autorizacion(menor, ms.AUT_NO_REQUERIDA, HOY) is None
    for estado in (ms.AUT_PENDIENTE, ms.AUT_APROBADA, ms.AUT_RECHAZADA):
        assert ms.estado_autorizacion(menor, estado, HOY) == estado


@pytest.mark.parametrize("estado", [None, "NO_REQUERIDA", "PENDIENTE", "RECHAZADA"])
def test_no_se_acepta_menor_sin_autorizacion_aprobada(estado: str | None) -> None:
    with pytest.raises(ConflictError) as exc:
        ms.validar_aceptacion_menor(date(2010, 3, 3), estado, HOY)
    assert exc.value.message == (
        "El voluntario es menor de edad y aún no tiene la autorización de su acudiente aprobada."
    )
    assert exc.value.status_code == 409


def test_se_acepta_menor_con_autorizacion_aprobada() -> None:
    ms.validar_aceptacion_menor(date(2010, 3, 3), ms.AUT_APROBADA, HOY)


@pytest.mark.parametrize("estado", [None, "PENDIENTE", "RECHAZADA", "APROBADA"])
def test_adulto_se_acepta_sin_importar_el_estado(estado: str | None) -> None:
    ms.validar_aceptacion_menor(date(2008, 6, 15), estado, HOY)  # cumple 18 hoy
    assert ms.puede_ser_aceptado(date(2008, 6, 15), estado, HOY)


def test_menor_que_cumple_18_manana_aun_se_bloquea() -> None:
    assert not ms.puede_ser_aceptado(date(2008, 6, 16), None, HOY)


# ─────────────── Validación de entradas ───────────────

def test_acudiente_valido_se_normaliza() -> None:
    a = AcudienteInput(
        acudiente_nombre="  María   José Pérez ",
        acudiente_documento="52.123.456",
        acudiente_telefono="(300) 123-4567",
        acudiente_parentesco="MADRE",
    )
    assert a.acudiente_nombre == "María José Pérez"
    assert a.acudiente_documento == "52123456"
    assert a.acudiente_telefono == "3001234567"


@pytest.mark.parametrize(
    "cambios",
    [
        {"acudiente_nombre": "Ana123"},
        {"acudiente_nombre": "A"},
        {"acudiente_documento": "12"},
        {"acudiente_documento": "1234<script>"},
        {"acudiente_telefono": "abc1234567"},
        {"acudiente_telefono": "12345"},
        {"acudiente_parentesco": "VECINO"},
        {"extra": "x"},
    ],
)
def test_acudiente_invalido(cambios: dict) -> None:
    base = {
        "acudiente_nombre": "Carlos Gómez",
        "acudiente_documento": "79123456",
        "acudiente_telefono": "3109876543",
        "acudiente_parentesco": "PADRE",
    }
    with pytest.raises(ValidationError):
        AcudienteInput(**{**base, **cambios})


def test_rechazo_exige_nota() -> None:
    with pytest.raises(ValidationError):
        ResolverAutorizacionInput(decision="RECHAZADA")
    assert ResolverAutorizacionInput(decision="APROBADA").nota is None


# ─────────────── Formato PDF ───────────────

def test_formato_pdf_se_genera() -> None:
    pdf = ms.generar_formato_pdf(
        nombre="Sofía Ñáñez",
        tipo_documento="TI",
        numero_documento="1012345678",
        fecha_nacimiento=date(2010, 2, 28),
        acudiente_parentesco="MADRE",
        hoy=HOY,
    )
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000
