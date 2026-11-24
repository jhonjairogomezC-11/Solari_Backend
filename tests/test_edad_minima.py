"""Regla de edad: mínimo 16 años para registrarse; 16-17 requieren acudiente."""

from __future__ import annotations

from datetime import date

import pytest

from app.core.edad import EDAD_MINIMA, MSG_EDAD_MINIMA, calcular_edad, validar_fecha_nacimiento
from app.services.menores_service import es_menor

HOY = date(2026, 11, 24)


def test_edad_minima_es_16():
    assert EDAD_MINIMA == 16


@pytest.mark.parametrize(
    "nacimiento",
    [date(2010, 11, 24), date(2008, 1, 1), date(1990, 5, 5)],  # 16 exactos, 18, adulto
)
def test_acepta_16_o_mas(nacimiento):
    assert validar_fecha_nacimiento(nacimiento, HOY) == nacimiento


@pytest.mark.parametrize("nacimiento", [date(2010, 11, 25), date(2012, 3, 3), date(2020, 1, 1)])
def test_rechaza_menores_de_16(nacimiento):
    with pytest.raises(ValueError, match="al menos 16"):
        validar_fecha_nacimiento(nacimiento, HOY)
    assert "16" in MSG_EDAD_MINIMA


def test_rechaza_fecha_futura():
    with pytest.raises(ValueError, match="futuro"):
        validar_fecha_nacimiento(date(2027, 1, 1), HOY)


def test_16_y_17_son_menores_y_requieren_acudiente():
    assert calcular_edad(date(2009, 6, 1), HOY) == 17
    assert es_menor(date(2009, 6, 1), HOY)
    assert es_menor(date(2010, 11, 24), HOY)
    assert not es_menor(date(2008, 11, 24), HOY)
