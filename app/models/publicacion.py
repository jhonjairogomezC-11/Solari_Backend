"""Modelo ORM de la tabla `publicaciones` y tabla pivote `publicacion_habilidades`."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Time,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# ENUMs nativos ya existentes en PostgreSQL — create_type=False
_modalidad_enum = ENUM(
    "PRESENCIAL", "VIRTUAL", "HIBRIDA",
    name="modalidad_tipo", create_type=False,
)
_estado_pub_enum = ENUM(
    "BORRADOR", "PENDIENTE_APROBACION", "PUBLICADA",
    "CERRADA", "CANCELADA", "COMPLETADA", "FINALIZADA",
    name="estado_publicacion", create_type=False,
)

# Estados de publicación como constantes
ESTADO_BORRADOR = "BORRADOR"
ESTADO_PENDIENTE_APROBACION = "PENDIENTE_APROBACION"
ESTADO_PUBLICADA = "PUBLICADA"
ESTADO_CERRADA = "CERRADA"
ESTADO_CANCELADA = "CANCELADA"
ESTADO_COMPLETADA = "COMPLETADA"
ESTADO_FINALIZADA = "FINALIZADA"

MODALIDAD_PRESENCIAL = "PRESENCIAL"
MODALIDAD_VIRTUAL = "VIRTUAL"
MODALIDAD_HIBRIDA = "HIBRIDA"

# Tabla pivote many-to-many publicaciones <-> habilidades
publicacion_habilidades = Table(
    "publicacion_habilidades",
    Base.metadata,
    Column(
        "publicacion_id",
        UUID(as_uuid=True),
        ForeignKey("publicaciones.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "habilidad_id",
        Integer,
        ForeignKey("habilidades.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Publicacion(Base):
    __tablename__ = "publicaciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    fundacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fundaciones.id", ondelete="CASCADE")
    )
    titulo: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text)
    categoria_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("areas_impacto.id", ondelete="RESTRICT")
    )
    modalidad: Mapped[str] = mapped_column(_modalidad_enum)
    municipio_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("municipios.id", ondelete="RESTRICT"), nullable=True
    )
    direccion_exacta: Mapped[str | None] = mapped_column(String(200), nullable=True)
    enlace_virtual: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    hora_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_fin: Mapped[time | None] = mapped_column(Time, nullable=True)
    cupo_maximo: Mapped[int] = mapped_column(Integer, default=1)
    edad_minima: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edad_maxima: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requisitos_adicionales: Mapped[str | None] = mapped_column(Text, nullable=True)
    imagen: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contacto_nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contacto_email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contacto_telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estado: Mapped[str] = mapped_column(_estado_pub_enum, default=ESTADO_BORRADOR)
    oculta_por_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_ocultamiento: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_ocultamiento: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_publicacion: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))

    # Relación many-to-many con habilidades (carga anticipada para serializar).
    habilidades: Mapped[list[Habilidad]] = relationship(  # noqa: F821
        "Habilidad",
        secondary=publicacion_habilidades,
        lazy="selectin",
    )
