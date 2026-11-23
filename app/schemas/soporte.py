from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.soporte import (
    CATEGORIAS_TICKET,
    TIPOS_SOLICITUD_CUENTA,
)


# ─────────────── Tickets ───────────────

class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria: str
    asunto: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(min_length=10, max_length=3000)
    adjunto_url: str | None = Field(default=None, max_length=500)

    @field_validator("categoria")
    @classmethod
    def _cat(cls, v: str) -> str:
        if v not in CATEGORIAS_TICKET:
            raise ValueError(f"categoria debe ser una de {CATEGORIAS_TICKET}")
        return v


class TicketMensajeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mensaje: str = Field(min_length=1, max_length=3000)
    adjunto_url: str | None = Field(default=None, max_length=500)


class TicketMensajeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    autor_id: uuid.UUID
    es_admin: bool
    mensaje: str
    adjunto_url: str | None = None
    fecha_creacion: datetime


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    numero: int
    categoria: str
    asunto: str
    descripcion: str
    adjunto_url: str | None = None
    estado: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class TicketDetalleOut(TicketOut):
    mensajes: list[TicketMensajeOut] = []


# ─────────────── Solicitudes de cuenta ───────────────

class SolicitudCuentaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo: str
    motivo: str | None = Field(default=None, max_length=2000)

    @field_validator("tipo")
    @classmethod
    def _tipo(cls, v: str) -> str:
        if v not in TIPOS_SOLICITUD_CUENTA:
            raise ValueError(f"tipo debe ser uno de {TIPOS_SOLICITUD_CUENTA}")
        return v


class SolicitudCuentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tipo: str
    motivo: str | None = None
    estado: str
    respuesta_admin: str | None = None
    fecha_atencion: datetime | None = None
    fecha_creacion: datetime
