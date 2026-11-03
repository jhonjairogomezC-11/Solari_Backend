"""Modelo ORM de la tabla `notificaciones`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_tipo_notif_enum = ENUM(
    "NUEVA_POSTULACION", "POSTULACION_RETIRADA",
    "VOLUNTARIO_ASISTIO", "VOLUNTARIO_NO_ASISTIO",
    "POSTULACION_ACEPTADA", "POSTULACION_RECHAZADA",
    "ACTIVIDAD_CANCELADA", "ACTIVIDAD_MODIFICADA",
    "FUNDACION_APROBADA", "FUNDACION_RECHAZADA",
    "FUNDACION_SUSPENDIDA", "FUNDACION_REACTIVADA",
    "RECORDATORIO_ACTIVIDAD",
    name="tipo_notificacion", create_type=False,
)

TIPO_NUEVA_POSTULACION = "NUEVA_POSTULACION"
TIPO_POSTULACION_RETIRADA = "POSTULACION_RETIRADA"
TIPO_POSTULACION_ACEPTADA = "POSTULACION_ACEPTADA"
TIPO_POSTULACION_RECHAZADA = "POSTULACION_RECHAZADA"
TIPO_VOLUNTARIO_ASISTIO = "VOLUNTARIO_ASISTIO"
TIPO_VOLUNTARIO_NO_ASISTIO = "VOLUNTARIO_NO_ASISTIO"
TIPO_ACTIVIDAD_CANCELADA = "ACTIVIDAD_CANCELADA"


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    tipo: Mapped[str] = mapped_column(_tipo_notif_enum)
    mensaje: Mapped[str] = mapped_column(Text)
    objeto_tipo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    objeto_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    leida: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_lectura: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
