"""Esquemas del panel admin: soporte, privacidad, verificación, reseñas y auditoría."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.soporte import ESTADOS_TICKET
from app.schemas.organizacion import DocumentoVerifOut
from app.schemas.soporte import TicketMensajeOut


class AdminTicketOut(BaseModel):
    id: uuid.UUID
    numero: int
    categoria: str
    asunto: str
    descripcion: str
    estado: str
    usuario_id: uuid.UUID
    usuario_nombre: str
    usuario_email: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    total_mensajes: int = 0


class AdminTicketDetalle(AdminTicketOut):
    mensajes: list[TicketMensajeOut] = []


class AdminResponderTicket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mensaje: str = Field(min_length=1, max_length=3000)
    estado: str | None = None

    @model_validator(mode="after")
    def validar(self) -> AdminResponderTicket:
        if self.estado is not None and self.estado not in ESTADOS_TICKET:
            raise ValueError(f"estado debe ser uno de {ESTADOS_TICKET}")
        return self


class AdminSolicitudOut(BaseModel):
    id: uuid.UUID
    tipo: str
    motivo: str | None = None
    estado: str
    respuesta_admin: str | None = None
    usuario_id: uuid.UUID
    usuario_nombre: str
    usuario_email: str
    usuario_rol: str
    fecha_creacion: datetime
    fecha_atencion: datetime | None = None


class AdminResolverSolicitud(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str
    respuesta: str | None = Field(default=None, max_length=2000)
    # Las acciones sobre la cuenta solo se ejecutan si el administrador lo pide de
    # forma explícita; aprobar por sí solo no modifica nada.
    ejecutar: bool = False

    @model_validator(mode="after")
    def validar(self) -> AdminResolverSolicitud:
        if self.decision not in ("EN_PROCESO", "APROBAR", "RECHAZAR"):
            raise ValueError("decision debe ser EN_PROCESO, APROBAR o RECHAZAR")
        return self


class AdminVerificacionOut(BaseModel):
    fundacion_id: uuid.UUID
    nombre: str
    nit: str | None = None
    tipo_organizacion: str
    constituida_legalmente: bool
    estado: str
    nota: str | None = None
    fecha: datetime | None = None
    documentos: list[DocumentoVerifOut] = []


class AdminResolverVerificacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accion: str
    nota: str | None = Field(default=None, max_length=1000)


class AdminResenaOut(BaseModel):
    id: uuid.UUID
    fundacion_id: uuid.UUID
    fundacion_nombre: str
    voluntario_nombre: str
    calificacion: int
    comentario: str
    estado: str
    motivo_moderacion: str | None = None
    fecha_creacion: datetime


class AdminModerarResena(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accion: str
    motivo: str | None = Field(default=None, max_length=500)


class AuditoriaOut(BaseModel):
    id: uuid.UUID
    admin_nombre: str
    tipo: str
    objeto_tipo: str | None = None
    objeto_id: uuid.UUID | None = None
    objeto_descripcion: str | None = None
    detalle_anterior: dict[str, Any] | None = None
    detalle_nuevo: dict[str, Any] | None = None
    motivo: str | None = None
    fecha_accion: datetime
