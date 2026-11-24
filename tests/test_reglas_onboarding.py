"""Reglas nuevas: perfil de voluntario obligatorio, fin de actividad y correo verificado."""

from __future__ import annotations

from datetime import date, time, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.perfil import VoluntarioPerfilInput
from app.services.postulacion_service import actividad_terminada

_BASE = {
    "tipo_documento": "CC",
    "numero_documento": "10203040",
    "fecha_nacimiento": "2000-01-01",
    "genero": "FEMENINO",
    "municipio_id": 1,
    "disponibilidad": "FLEXIBLE",
    "direccion": "Calle 10 # 5-20",
    "telefono_contacto": "3001234567",
    "contacto_emergencia_nombre": "María Pérez",
    "contacto_emergencia_telefono": "3109876543",
}


def test_perfil_completo_es_valido():
    VoluntarioPerfilInput(**_BASE)


@pytest.mark.parametrize(
    "campo",
    ["direccion", "telefono_contacto", "contacto_emergencia_nombre", "contacto_emergencia_telefono"],
)
def test_perfil_exige_contacto_y_emergencia(campo):
    with pytest.raises(ValidationError):
        VoluntarioPerfilInput(**{**_BASE, campo: "  "})


def test_perfil_rechaza_telefono_invalido():
    with pytest.raises(ValidationError):
        VoluntarioPerfilInput(**{**_BASE, "contacto_emergencia_telefono": "abc"})


def _pub(fecha_fin: date, hora_fin: time | None = None, estado: str = "PUBLICADA"):
    return SimpleNamespace(fecha_fin=fecha_fin, hora_fin=hora_fin, estado=estado)


def test_actividad_futura_no_terminada():
    assert not actividad_terminada(_pub(date.today() + timedelta(days=3)))


def test_actividad_pasada_terminada():
    assert actividad_terminada(_pub(date.today() - timedelta(days=1)))


def test_actividad_finalizada_por_estado():
    assert actividad_terminada(_pub(date.today() + timedelta(days=3), estado="FINALIZADA"))
