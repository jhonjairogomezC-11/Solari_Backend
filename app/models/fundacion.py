"""Modelo ORM de la tabla existente `fundaciones`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_estado_verif_enum = ENUM(
    "PENDIENTE", "APROBADA", "RECHAZADA", "SUSPENDIDA",
    name="estado_verificacion", create_type=False,
)

ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_APROBADA = "APROBADA"
ESTADO_RECHAZADA = "RECHAZADA"
ESTADO_SUSPENDIDA = "SUSPENDIDA"


class Fundacion(Base):
    __tablename__ = "fundaciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True
    )
    nombre: Mapped[str] = mapped_column(String(150))
    nit: Mapped[str] = mapped_column(String(20), unique=True)
    representante_legal: Mapped[str] = mapped_column(String(150))
    correo_institucional: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telefono: Mapped[str] = mapped_column(String(20))
    direccion: Mapped[str] = mapped_column(String(200))
    municipio_id: Mapped[int] = mapped_column(Integer)
    pagina_web: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descripcion: Mapped[str] = mapped_column(Text)
    documento_legal: Mapped[str] = mapped_column(Text)
    logo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado_verificacion: Mapped[str] = mapped_column(
        _estado_verif_enum, default=ESTADO_PENDIENTE
    )
    fecha_verificacion: Mapped[datetime | None] = mapped_column(nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
