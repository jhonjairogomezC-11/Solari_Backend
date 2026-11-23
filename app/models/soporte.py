"""Modelos del centro de soporte: tickets, mensajes y solicitudes de cuenta.

Tablas NUEVAS y aditivas.

- `tickets_soporte`: solicitudes del usuario con categoría, asunto, estado.
  El `numero` es un consecutivo legible (ej. SOL-000123) además del UUID.
- `ticket_mensajes`: hilo de conversación (usuario ↔ administrador).
- `solicitudes_cuenta`: bloqueo/inhabilitación/eliminación de cuenta o datos,
  con flujo administrativo (no se ejecutan automáticamente).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Sequence,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Categorías de ticket ──
CAT_ACCESO = "PROBLEMAS_ACCESO"
CAT_CUENTA = "PROBLEMAS_CUENTA"
CAT_PLATAFORMA = "ERRORES_PLATAFORMA"
CAT_POSTULACIONES = "PROBLEMAS_POSTULACIONES"
CAT_CONVOCATORIAS = "PROBLEMAS_CONVOCATORIAS"
CAT_NOTIFICACIONES = "PROBLEMAS_NOTIFICACIONES"
CAT_DATOS = "PROTECCION_DATOS"
CAT_ADMINISTRATIVO = "SOLICITUDES_ADMINISTRATIVAS"
CAT_OTROS = "OTROS"

CATEGORIAS_TICKET = (
    CAT_ACCESO, CAT_CUENTA, CAT_PLATAFORMA, CAT_POSTULACIONES,
    CAT_CONVOCATORIAS, CAT_NOTIFICACIONES, CAT_DATOS, CAT_ADMINISTRATIVO, CAT_OTROS,
)

# ── Estados de ticket ──
ESTADO_ABIERTO = "ABIERTO"
ESTADO_EN_REVISION = "EN_REVISION"
ESTADO_PENDIENTE_INFO = "PENDIENTE_INFORMACION"
ESTADO_RESUELTO = "RESUELTO"
ESTADO_CERRADO = "CERRADO"

ESTADOS_TICKET = (
    ESTADO_ABIERTO, ESTADO_EN_REVISION, ESTADO_PENDIENTE_INFO,
    ESTADO_RESUELTO, ESTADO_CERRADO,
)

# ── Tipos de solicitud de cuenta ──
SOL_BLOQUEO_TEMPORAL = "BLOQUEO_TEMPORAL"
SOL_INHABILITACION = "INHABILITACION"
SOL_ELIMINACION_CUENTA = "ELIMINACION_CUENTA"
SOL_ELIMINACION_DATOS = "ELIMINACION_DATOS"
SOL_ACCESO_SOSPECHOSO = "REPORTE_ACCESO_SOSPECHOSO"
SOL_ACTIVIDAD_NO_AUTORIZADA = "REPORTE_ACTIVIDAD_NO_AUTORIZADA"

TIPOS_SOLICITUD_CUENTA = (
    SOL_BLOQUEO_TEMPORAL, SOL_INHABILITACION, SOL_ELIMINACION_CUENTA,
    SOL_ELIMINACION_DATOS, SOL_ACCESO_SOSPECHOSO, SOL_ACTIVIDAD_NO_AUTORIZADA,
)

SOL_ESTADO_PENDIENTE = "PENDIENTE"
SOL_ESTADO_EN_PROCESO = "EN_PROCESO"
SOL_ESTADO_APROBADA = "APROBADA"
SOL_ESTADO_RECHAZADA = "RECHAZADA"
SOL_ESTADO_COMPLETADA = "COMPLETADA"

ESTADOS_SOLICITUD = (
    SOL_ESTADO_PENDIENTE, SOL_ESTADO_EN_PROCESO, SOL_ESTADO_APROBADA,
    SOL_ESTADO_RECHAZADA, SOL_ESTADO_COMPLETADA,
)

_ticket_seq = Sequence("ticket_numero_seq", start=1)


class TicketSoporte(Base):
    __tablename__ = "tickets_soporte"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    numero: Mapped[int] = mapped_column(
        BigInteger, _ticket_seq, server_default=_ticket_seq.next_value(), unique=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    categoria: Mapped[str] = mapped_column(String(40))
    asunto: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text)
    adjunto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), default=ESTADO_ABIERTO)
    fecha_creacion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )


class TicketMensaje(Base):
    __tablename__ = "ticket_mensajes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets_soporte.id", ondelete="CASCADE")
    )
    autor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    es_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    mensaje: Mapped[str] = mapped_column(Text)
    adjunto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )


class SolicitudCuenta(Base):
    __tablename__ = "solicitudes_cuenta"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    tipo: Mapped[str] = mapped_column(String(40))
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(30), default=SOL_ESTADO_PENDIENTE)
    respuesta_admin: Mapped[str | None] = mapped_column(Text, nullable=True)
    atendida_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    fecha_atencion: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )
