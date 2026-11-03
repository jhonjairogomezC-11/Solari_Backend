from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.catalogo import HabilidadOut

MODALIDADES = ("PRESENCIAL", "VIRTUAL", "HIBRIDA")
ESTADOS_PUB = (
    "BORRADOR", "PENDIENTE_APROBACION", "PUBLICADA",
    "CERRADA", "CANCELADA", "COMPLETADA", "FINALIZADA",
)


class FundacionResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    logo: str | None = None


class PublicacionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(min_length=10)
    categoria_id: int = Field(gt=0)
    modalidad: str
    municipio_id: int | None = None
    direccion_exacta: str | None = Field(default=None, max_length=200)
    enlace_virtual: str | None = None
    fecha_inicio: date
    fecha_fin: date
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cupo_maximo: int = Field(default=1, ge=1)
    edad_minima: int | None = Field(default=None, ge=14)
    edad_maxima: int | None = None
    requisitos_adicionales: str | None = None
    contacto_nombre: str | None = Field(default=None, max_length=150)
    contacto_email: str | None = Field(default=None, max_length=150)
    contacto_telefono: str | None = Field(default=None, max_length=20)
    habilidades: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_campos(self) -> PublicacionCreate:
        if self.modalidad not in MODALIDADES:
            raise ValueError(f"modalidad debe ser uno de {MODALIDADES}")
        if self.modalidad in ("PRESENCIAL", "HIBRIDA") and not self.municipio_id:
            raise ValueError("municipio_id es obligatorio para modalidad PRESENCIAL o HIBRIDA.")
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin debe ser mayor o igual a fecha_inicio.")
        if self.edad_minima and self.edad_maxima and self.edad_maxima < self.edad_minima:
            raise ValueError("edad_maxima debe ser mayor o igual a edad_minima.")
        return self


class PublicacionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = None
    categoria_id: int | None = Field(default=None, gt=0)
    modalidad: str | None = None
    municipio_id: int | None = None
    direccion_exacta: str | None = Field(default=None, max_length=200)
    enlace_virtual: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cupo_maximo: int | None = Field(default=None, ge=1)
    edad_minima: int | None = Field(default=None, ge=14)
    edad_maxima: int | None = None
    requisitos_adicionales: str | None = None
    contacto_nombre: str | None = Field(default=None, max_length=150)
    contacto_email: str | None = Field(default=None, max_length=150)
    contacto_telefono: str | None = Field(default=None, max_length=20)
    habilidades: list[int] | None = None

    @model_validator(mode="after")
    def validar_campos(self) -> PublicacionUpdate:
        if self.modalidad and self.modalidad not in MODALIDADES:
            raise ValueError(f"modalidad debe ser uno de {MODALIDADES}")
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin debe ser mayor o igual a fecha_inicio.")
        return self


class PublicacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    descripcion: str
    modalidad: str
    estado: str
    fecha_inicio: date
    fecha_fin: date
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cupo_maximo: int
    edad_minima: int | None = None
    edad_maxima: int | None = None
    requisitos_adicionales: str | None = None
    direccion_exacta: str | None = None
    enlace_virtual: str | None = None
    imagen: str | None = None
    contacto_nombre: str | None = None
    contacto_email: str | None = None
    contacto_telefono: str | None = None
    fecha_publicacion: datetime | None = None
    fecha_creacion: datetime
    fundacion_id: uuid.UUID
    categoria_id: int
    municipio_id: int | None = None
    habilidades: list[HabilidadOut] = []


class PublicacionConRelaciones(PublicacionOut):
    """Versión con relaciones resueltas (para detalle y listados ricos)."""
    habilidades: list[HabilidadOut] = []


class PaginatedResponse[T](BaseModel):
    data: list[T]
    total: int
    page: int
    per_page: int
    pages: int
