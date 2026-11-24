"""Reglas de edad de Solari (funciones puras, sin base de datos).

- EDAD_MINIMA = 16: nadie menor de 16 años puede registrarse ni participar.
- Entre 16 y 17 años (menor de MAYORIA_EDAD) se exige la autorización del acudiente
  antes de que una organización pueda aceptar la postulación.
- La edad se calcula con la fecha actual de Bogotá (UTC-5, sin horario de verano).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

EDAD_MINIMA = 16
MAYORIA_EDAD = 18

MSG_EDAD_MINIMA = f"Debes tener al menos {EDAD_MINIMA} años para registrarte en Solari."

_TZ_BOGOTA = timezone(timedelta(hours=-5), "America/Bogota")


def hoy_bogota() -> date:
    """Fecha actual en Bogotá."""
    return datetime.now(_TZ_BOGOTA).date()


def calcular_edad(nacimiento: date, hoy: date | None = None) -> int:
    """Años cumplidos. Quien nació un 29 de febrero los cumple el 1 de marzo en años no bisiestos."""
    hoy = hoy or hoy_bogota()
    return hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))


def validar_fecha_nacimiento(nacimiento: date, hoy: date | None = None) -> date:
    """Para validadores de Pydantic: rechaza fechas futuras y menores de EDAD_MINIMA."""
    hoy = hoy or hoy_bogota()
    if nacimiento > hoy:
        raise ValueError("La fecha de nacimiento no puede estar en el futuro.")
    if calcular_edad(nacimiento, hoy) > 110:
        raise ValueError("Revisa la fecha de nacimiento.")
    if calcular_edad(nacimiento, hoy) < EDAD_MINIMA:
        raise ValueError(MSG_EDAD_MINIMA)
    return nacimiento
