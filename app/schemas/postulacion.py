from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.publicacion import PaginatedResponse

__all__ = [
    "ConfirmarAsistencia",
    "HistorialOut",
    "PaginatedResponse",
    "PostulacionCreate",
    "PostulacionOut",
    "PostulacionResponder",
    "PostulanteOut",
    "PostulantesPage",
    "ResumenCupos",
    "RetirarInput",
]

ESTADOS_POSTULACION = (
    "PENDIENTE", "EN_REVISION", "ACEPTADO", "RECHAZADO", "LISTA_ESPERA",
    "RETIRADO", "CANCELADO_FUNDACION", "ASISTIO", "NO_ASISTIO",
)
# Decisiones que puede tomar la organización sobre una postulación.
ESTADOS_RESPUESTA_ORG = ("ACEPTADO", "RECHAZADO", "EN_REVISION", "LISTA_ESPERA")


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
    # El motivo es opcional: el rechazo usa una plantilla respetuosa (R6), de modo
    # que la organización no tenga que redactar mensajes personalizados.
    motivo_rechazo: str | None = Field(default=None, max_length=500)
    calificacion: int | None = Field(default=None, ge=1, le=5)
    comentario_fundacion: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validar_estado(self) -> PostulacionResponder:
        if self.estado not in ESTADOS_RESPUESTA_ORG:
            raise ValueError(f"estado debe ser uno de {ESTADOS_RESPUESTA_ORG}")
        return self


class RetirarInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Obligatorio en la práctica cuando el voluntario ya fue aceptado (R7).
    confirmar: bool = False
    motivo: str | None = Field(default=None, max_length=500)


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
    fecha_actualizacion: datetime | None = None
    publicacion_id: uuid.UUID
    voluntario_id: uuid.UUID


class HistorialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    estado_anterior: str | None = None
    estado_nuevo: str
    rol_actor: str | None = None
    motivo: str | None = None
    fecha: datetime


# ─────────────── Panel de la organización ───────────────


class VoluntarioPostulante(BaseModel):
    """Datos del voluntario visibles para la organización que evalúa su postulación.

    Privacidad: NO incluye documento, fecha de nacimiento, dirección, teléfono ni
    contacto de emergencia; esos datos quedan bajo control del voluntario.
    """

    nombre: str
    foto_perfil: str | None = None
    municipio: str | None = None
    disponibilidad: str
    experiencia: str | None = None
    descripcion: str | None = None
    idiomas: str | None = None
    profesion: str | None = None
    esta_verificado: bool = False
    horas_acumuladas: int = 0
    actividades_completadas: int = 0
    xp_total: int = 0
    habilidades: list[str] = []
    habilidades_coinciden: list[str] = []
    coincidencia: int = 0


class PostulanteOut(PostulacionOut):
    voluntario: VoluntarioPostulante | None = None


class ResumenCupos(BaseModel):
    cupo_maximo: int
    aceptados: int
    disponibles: int
    pendientes: int
    lista_espera: int


class PostulantesPage(BaseModel):
    data: list[PostulanteOut]
    total: int
    page: int
    per_page: int
    pages: int
    resumen: ResumenCupos
