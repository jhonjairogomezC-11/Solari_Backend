from __future__ import annotations

import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

TIPO_DOC = ("CC", "TI", "CE", "PASAPORTE")
GENEROS = ("MASCULINO", "FEMENINO", "OTRO")
DISPONIBILIDAD = ("ENTRE_SEMANA", "FINES_DE_SEMANA", "FLEXIBLE")


# ─────────────── Voluntario ───────────────

class VoluntarioPerfilInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo_documento: str
    numero_documento: str = Field(min_length=4, max_length=30)
    fecha_nacimiento: date
    genero: str
    municipio_id: int = Field(gt=0)
    disponibilidad: str
    experiencia: str | None = Field(default=None, max_length=1000)

    @field_validator("tipo_documento")
    @classmethod
    def _tipo(cls, v: str) -> str:
        if v not in TIPO_DOC:
            raise ValueError(f"tipo_documento debe ser uno de {TIPO_DOC}")
        return v

    @field_validator("genero")
    @classmethod
    def _genero(cls, v: str) -> str:
        if v not in GENEROS:
            raise ValueError(f"genero debe ser uno de {GENEROS}")
        return v

    @field_validator("disponibilidad")
    @classmethod
    def _disp(cls, v: str) -> str:
        if v not in DISPONIBILIDAD:
            raise ValueError(f"disponibilidad debe ser uno de {DISPONIBILIDAD}")
        return v


class VoluntarioPerfilOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID
    tipo_documento: str
    numero_documento: str
    fecha_nacimiento: date
    genero: str
    municipio_id: int
    disponibilidad: str
    experiencia: str | None = None
    esta_verificado: bool
    fecha_creacion: datetime


# ─────────────── Fundación ───────────────

class FundacionPerfilInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre_fundacion: str = Field(min_length=2, max_length=150)
    nit: str
    representante_legal: str = Field(min_length=2, max_length=150)
    correo_institucional: str | None = Field(default=None, max_length=150)
    telefono_contacto: str = Field(min_length=7, max_length=20)
    direccion: str = Field(min_length=4, max_length=200)
    municipio_id: int = Field(gt=0)
    descripcion: str = Field(min_length=10, max_length=1000)
    documento_legal: str = Field(min_length=3, max_length=255)
    pagina_web: str | None = Field(default=None, max_length=255)

    @field_validator("nit")
    @classmethod
    def _nit(cls, v: str) -> str:
        if not re.fullmatch(r"\d{7,10}-\d", v):
            raise ValueError("El NIT debe tener el formato 000000000-0.")
        return v


class FundacionPerfilOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID
    nombre: str
    nit: str
    representante_legal: str
    correo_institucional: str | None = None
    telefono: str
    direccion: str
    municipio_id: int
    descripcion: str
    pagina_web: str | None = None
    estado_verificacion: str
    fecha_creacion: datetime


class PerfilEstado(BaseModel):
    """Indica si el usuario ya tiene su perfil de dominio completo."""
    rol: str
    perfil_completo: bool
