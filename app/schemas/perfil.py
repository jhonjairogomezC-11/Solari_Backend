from __future__ import annotations

import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TIPO_DOC = ("CC", "TI", "CE", "PASAPORTE")
GENEROS = ("MASCULINO", "FEMENINO", "OTRO")
DISPONIBILIDAD = ("ENTRE_SEMANA", "FINES_DE_SEMANA", "FLEXIBLE")


# ─────────────── Voluntario ───────────────

MODALIDAD_PREF = ("PRESENCIAL", "VIRTUAL", "HIBRIDA", "INDIFERENTE")


class VoluntarioPerfilInput(BaseModel):
    """Entrada de creación/actualización de perfil de voluntario.

    Los campos de identidad (tipo_documento, numero_documento, fecha_nacimiento,
    genero) SOLO se usan al CREAR el perfil. En actualizaciones posteriores son
    inmutables: el servicio los ignora y conserva los valores originales. Para
    corregirlos se requiere un procedimiento administrativo (auditado).
    """

    model_config = ConfigDict(extra="forbid")

    # Identidad (inmutable tras el registro)
    tipo_documento: str
    numero_documento: str = Field(min_length=4, max_length=30)
    fecha_nacimiento: date
    genero: str
    # Editables
    municipio_id: int = Field(gt=0)
    disponibilidad: str
    experiencia: str | None = Field(default=None, max_length=1000)
    direccion: str | None = Field(default=None, max_length=200)
    descripcion: str | None = Field(default=None, max_length=1000)
    telefono_contacto: str | None = Field(default=None, max_length=20)
    nivel_educativo: str | None = Field(default=None, max_length=100)
    profesion: str | None = Field(default=None, max_length=150)
    idiomas: str | None = Field(default=None, max_length=300)
    preferencia_modalidad: str | None = Field(default=None, max_length=20)
    contacto_emergencia_nombre: str | None = Field(default=None, max_length=150)
    contacto_emergencia_telefono: str | None = Field(default=None, max_length=20)

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

    @field_validator("preferencia_modalidad")
    @classmethod
    def _pref(cls, v: str | None) -> str | None:
        if v is not None and v not in MODALIDAD_PREF:
            raise ValueError(f"preferencia_modalidad debe ser uno de {MODALIDAD_PREF}")
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
    foto_perfil: str | None = None
    documento_identidad: str | None = None
    esta_verificado: bool
    direccion: str | None = None
    descripcion: str | None = None
    telefono_contacto: str | None = None
    nivel_educativo: str | None = None
    profesion: str | None = None
    idiomas: str | None = None
    preferencia_modalidad: str | None = None
    contacto_emergencia_nombre: str | None = None
    contacto_emergencia_telefono: str | None = None
    horas_acumuladas: int = 0
    actividades_completadas: int = 0
    fecha_creacion: datetime


# ─────────────── Fundación ───────────────

TIPOS_ORGANIZACION = ("FUNDACION", "REFUGIO", "COLECTIVO", "INICIATIVA_CIUDADANA", "OTRA")


class FundacionPerfilInput(BaseModel):
    """Perfil de la organización.

    Pueden participar organizaciones sin constitución legal (refugios, colectivos):
    en ese caso NIT y documento legal son opcionales (regla R13).
    """

    model_config = ConfigDict(extra="forbid")

    nombre_fundacion: str = Field(min_length=2, max_length=150)
    tipo_organizacion: str = "FUNDACION"
    constituida_legalmente: bool = True
    nit: str | None = None
    representante_legal: str = Field(min_length=2, max_length=150)
    correo_institucional: str | None = Field(default=None, max_length=150)
    telefono_contacto: str = Field(min_length=7, max_length=20)
    direccion: str = Field(min_length=4, max_length=200)
    municipio_id: int = Field(gt=0)
    descripcion: str = Field(min_length=10, max_length=1000)
    documento_legal: str | None = Field(default=None, max_length=255)
    pagina_web: str | None = Field(default=None, max_length=255)

    @field_validator("tipo_organizacion")
    @classmethod
    def _tipo(cls, v: str) -> str:
        if v not in TIPOS_ORGANIZACION:
            raise ValueError(f"tipo_organizacion debe ser uno de {TIPOS_ORGANIZACION}")
        return v

    @field_validator("nit", "documento_legal", mode="before")
    @classmethod
    def _vacio_a_none(cls, v: object) -> object:
        return None if isinstance(v, str) and not v.strip() else v

    @field_validator("nit")
    @classmethod
    def _nit(cls, v: str | None) -> str | None:
        if v is not None and not re.fullmatch(r"\d{7,10}-\d", v):
            raise ValueError("El NIT debe tener el formato 000000000-0.")
        return v

    @model_validator(mode="after")
    def _constituida_requiere_documentos(self) -> FundacionPerfilInput:
        if self.constituida_legalmente and not (self.nit and self.documento_legal):
            raise ValueError(
                "Una organización constituida legalmente debe indicar NIT y documento legal."
            )
        return self


class FundacionPerfilOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID
    nombre: str
    nit: str | None = None
    tipo_organizacion: str = "FUNDACION"
    constituida_legalmente: bool = True
    representante_legal: str
    correo_institucional: str | None = None
    telefono: str
    direccion: str
    municipio_id: int
    descripcion: str
    pagina_web: str | None = None
    logo: str | None = None
    documento_legal: str | None = None
    historia: str | None = None
    mision: str | None = None
    mostrar_telefono: bool = False
    mostrar_correo: bool = False
    mostrar_direccion: bool = False
    verificacion_documental: str = "NO_SOLICITADA"
    verificacion_documental_nota: str | None = None
    estado_verificacion: str
    fecha_creacion: datetime


class ArchivoSubidoOut(BaseModel):
    """Respuesta tras subir un archivo."""
    url: str


class PerfilEstado(BaseModel):
    """Indica si el usuario ya tiene su perfil de dominio completo."""
    rol: str
    perfil_completo: bool
