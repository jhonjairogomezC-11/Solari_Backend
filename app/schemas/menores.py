"""Entradas y salidas de la autorización del acudiente (voluntarios menores de edad)."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PARENTESCOS = ("MADRE", "PADRE", "TUTOR_LEGAL", "OTRO")

_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$")
_DOCUMENTO = re.compile(r"^[A-Za-z0-9-]{5,20}$")


class AcudienteInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    acudiente_nombre: str = Field(min_length=3, max_length=150)
    acudiente_documento: str = Field(min_length=5, max_length=20)
    acudiente_telefono: str = Field(min_length=7, max_length=20)
    acudiente_parentesco: Literal["MADRE", "PADRE", "TUTOR_LEGAL", "OTRO"]

    @field_validator("acudiente_nombre")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = " ".join(v.split())
        if not _NOMBRE.fullmatch(v) or len(v.replace(" ", "")) < 3:
            raise ValueError("Escribe el nombre completo del acudiente (solo letras).")
        return v

    @field_validator("acudiente_documento")
    @classmethod
    def _documento(cls, v: str) -> str:
        v = v.replace(".", "").replace(" ", "").upper()
        if not _DOCUMENTO.fullmatch(v):
            raise ValueError("El documento debe tener entre 5 y 20 letras o números.")
        return v

    @field_validator("acudiente_telefono")
    @classmethod
    def _telefono(cls, v: str) -> str:
        limpio = re.sub(r"[\s()-]", "", v)
        if not re.fullmatch(r"\+?\d{7,15}", limpio):
            raise ValueError("Escribe un teléfono válido (de 7 a 15 dígitos).")
        return limpio


class AutorizacionOut(BaseModel):
    """Estado de la autorización del acudiente para el propio voluntario."""

    es_menor: bool
    edad: int
    requerida: bool
    # NO_REQUERIDA (mayor de edad) | PENDIENTE | APROBADA | RECHAZADA | None (sin enviar)
    estado: str | None = None
    acudiente_nombre: str | None = None
    acudiente_documento: str | None = None
    acudiente_telefono: str | None = None
    acudiente_parentesco: str | None = None
    archivo: str | None = None
    fecha: datetime | None = None
    nota: str | None = None


class AdminAutorizacionOut(BaseModel):
    voluntario_id: uuid.UUID
    usuario_id: uuid.UUID
    nombre: str
    email: str
    edad: int
    fecha_nacimiento: date
    tipo_documento: str
    numero_documento: str
    acudiente_nombre: str | None = None
    acudiente_documento: str | None = None
    acudiente_telefono: str | None = None
    acudiente_parentesco: str | None = None
    archivo: str | None = None
    estado: str | None = None
    fecha: datetime | None = None
    nota: str | None = None


class AdminAutorizacionesPage(BaseModel):
    data: list[AdminAutorizacionOut]
    total: int
    page: int
    per_page: int
    pages: int


class ResolverAutorizacionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: Literal["APROBADA", "RECHAZADA"]
    nota: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _nota_si_rechaza(self) -> ResolverAutorizacionInput:
        if self.decision == "RECHAZADA" and not self.nota:
            raise ValueError("Indica el motivo del rechazo para que el voluntario pueda corregirlo.")
        return self
