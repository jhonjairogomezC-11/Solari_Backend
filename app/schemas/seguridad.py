"""Esquemas de seguridad de cuenta: sesiones activas y verificación en dos pasos.

Nunca incluyen valores ni hashes de tokens, ni el secreto TOTP guardado.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ─────────────────────────── Sesiones ───────────────────────────


class SesionOut(BaseModel):
    id: uuid.UUID
    dispositivo: str
    ip: str | None = None
    fecha_inicio: datetime | None = None
    fecha_ultimo_uso: datetime | None = None
    expiracion: datetime
    actual: bool = False


class SesionesRevocadasOut(BaseModel):
    message: str
    revocadas: int


# ─────────────────────────── MFA ───────────────────────────


class MfaEstadoOut(BaseModel):
    activo: bool
    codigos_respaldo_restantes: int = 0
    recomendado: bool = False


class MfaIniciarOut(BaseModel):
    otpauth_uri: str
    qr_svg: str
    # Clave para ingreso manual en la app autenticadora (solo durante la activación).
    secreto: str


class MfaCodigoInput(BaseModel):
    codigo: str = Field(min_length=6, max_length=20)


class MfaConfirmarOut(BaseModel):
    message: str
    codigos_respaldo: list[str]


class MfaDesactivarInput(BaseModel):
    password: str | None = Field(default=None, max_length=200)
    codigo: str = Field(min_length=6, max_length=20)


class MfaRequeridoResponse(BaseModel):
    """Respuesta de login cuando la cuenta tiene verificación en dos pasos."""

    mfa_requerido: Literal[True] = True
    mfa_token: str
    expires_in: int
    message: str = "Ingresa el código de tu app autenticadora para continuar."


class LoginMfaRequest(BaseModel):
    mfa_token: str = Field(min_length=1, max_length=2000)
    codigo: str = Field(min_length=6, max_length=20)
