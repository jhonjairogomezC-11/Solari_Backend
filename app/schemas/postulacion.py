from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.publicacion import PaginatedResponse

__all__ = [
    "ConfirmarAsistencia",
    "PaginatedResponse",
    "PostulacionCreate",
    "PostulacionOut",
    "PostulacionResponder",
]

ESTADOS_POSTULACION = ("PENDIENTE", "ACEPTADO", "RECHAZADO", "RETIRADO", "ASISTIO", "NO_ASISTIO")


class VoluntarioResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    usuario_id: uuid.UUID


class PostulacionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    publicacion_id: uuid.UUID
    mensaje_voluntario: str | None = Field(default=None, max_length=1000)


class PostulacionResponder(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: str
    motivo_rechazo: str | None = Field(default=None, max_length=500)
    calificacion: int | None = Field(default=None, ge=1, le=5)
    comentario_fundacion: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validar_estado(self) -> PostulacionResponder:
        if self.estado not in ESTADOS_POSTULACION:
            raise ValueError(f"estado debe ser uno de {ESTADOS_POSTULACION}")
        if self.estado == "RECHAZADO" and not self.motivo_rechazo:
            raise ValueError("motivo_rechazo es obligatorio cuando el estado es RECHAZADO.")
        return self


class ConfirmarAsistencia(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asistio: bool
    calificacion: int | None = Field(default=None, ge=1, le=5)
    comentario_fundacion: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validar(self) -> ConfirmarAsistencia:
        if self.asistio and not self.calificacion:
            raise ValueError("calificacion es obligatoria cuando asistio es true.")
        return self


class PostulacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    estado: str
    mensaje_voluntario: str | None = None
    motivo_rechazo: str | None = None
    calificacion: int | None = None
    comentario_fundacion: str | None = None
    fecha_postulacion: datetime
    fecha_respuesta: datetime | None = None
    fecha_confirmacion: datetime | None = None
    publicacion_id: uuid.UUID
    voluntario_id: uuid.UUID
