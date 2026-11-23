from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class VerificacionCertificadoOut(BaseModel):
    """Resultado público de verificar un certificado (sin datos personales completos)."""

    valido: bool
    voluntario: str | None = None
    actividad: str | None = None
    organizacion: str | None = None
    horas: int | None = None
    fecha: date | None = None
