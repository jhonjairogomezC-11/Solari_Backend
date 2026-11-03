"""Modelo ORM de la tabla `postulaciones`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_estado_post_enum = ENUM(
    "PENDIENTE", "ACEPTADO", "RECHAZADO", "RETIRADO", "ASISTIO", "NO_ASISTIO",
    name="estado_postulacion", create_type=False,
)

ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_ACEPTADO = "ACEPTADO"
ESTADO_RECHAZADO = "RECHAZADO"
ESTADO_RETIRADO = "RETIRADO"
ESTADO_ASISTIO = "ASISTIO"
ESTADO_NO_ASISTIO = "NO_ASISTIO"


class Postulacion(Base):
    __tablename__ = "postulaciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    publicacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publicaciones.id", ondelete="CASCADE")
    )
    voluntario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voluntarios.id", ondelete="CASCADE")
    )
    estado: Mapped[str] = mapped_column(_estado_post_enum, default=ESTADO_PENDIENTE)
    mensaje_voluntario: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_respuesta: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_confirmacion: Mapped[datetime | None] = mapped_column(nullable=True)
    calificacion: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    comentario_fundacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_postulacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
