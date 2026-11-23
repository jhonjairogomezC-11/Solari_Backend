"""Modelos de intereses y gamificación del voluntario.

IMPORTANTE: estas tablas YA EXISTEN en la BD (creadas por Laravel). Aquí solo se
mapean a su esquema real, sin crearlas ni modificarlas.

Sistema de puntos existente:
- `voluntario_puntos`: saldo y total histórico (1:1 con voluntario).
- `transacciones_puntos`: historial auditable (base + bonus + total, por postulación).
- `logros`: catálogo (codigo, nombre, descripcion, icono, tipo, umbral, activo).
- `voluntario_logros`: logros obtenidos (único lógico por voluntario+logro).
- `intereses` / `voluntario_intereses`: catálogo y selección del voluntario.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Tipos de condición de logro (valores REALES de la columna `tipo` en la BD).
LOGRO_PARTICIPACIONES = "participaciones"  # umbral = nº actividades asistidas
LOGRO_PUNTOS = "puntos"                    # umbral = XP total histórico
LOGRO_DIFICULTAD = "dificultad"            # actividades de dificultad alta
LOGRO_URGENTE = "urgente"                  # umbral = nº convocatorias urgentes


class Interes(Base):
    __tablename__ = "intereses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)


class VoluntarioInteres(Base):
    __tablename__ = "voluntario_intereses"

    voluntario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voluntarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    interes_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("intereses.id", ondelete="CASCADE"), primary_key=True
    )


class Logro(Base):
    __tablename__ = "logros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String, unique=True)
    nombre: Mapped[str] = mapped_column(String)
    descripcion: Mapped[str] = mapped_column(Text)
    icono: Mapped[str | None] = mapped_column(String, nullable=True)
    tipo: Mapped[str] = mapped_column(String)
    umbral: Mapped[int] = mapped_column(Integer, default=1)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class VoluntarioLogro(Base):
    __tablename__ = "voluntario_logros"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    voluntario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voluntarios.id", ondelete="CASCADE")
    )
    logro_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("logros.id", ondelete="CASCADE")
    )
    fecha_obtencion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )


class VoluntarioPuntos(Base):
    """Saldo de puntos (XP) del voluntario (1:1)."""

    __tablename__ = "voluntario_puntos"

    voluntario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voluntarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    saldo: Mapped[int] = mapped_column(Integer, default=0)
    total_historico: Mapped[int] = mapped_column(Integer, default=0)
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )


class TransaccionPuntos(Base):
    """Historial auditable de movimientos de puntos (XP)."""

    __tablename__ = "transacciones_puntos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    voluntario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voluntarios.id", ondelete="CASCADE")
    )
    postulacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("postulaciones.id", ondelete="SET NULL"),
        nullable=True,
    )
    puntos_base: Mapped[int] = mapped_column(Integer, default=0)
    puntos_bonus: Mapped[int] = mapped_column(Integer, default=0)
    puntos_total: Mapped[int] = mapped_column(Integer, default=0)
    motivo: Mapped[str] = mapped_column(String)
    fecha: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))


class PublicacionImagen(Base):
    """Galería de imágenes de una convocatoria (ya existente)."""

    __tablename__ = "publicacion_imagenes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    publicacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publicaciones.id", ondelete="CASCADE")
    )
    ruta: Mapped[str] = mapped_column(String)
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)
    fecha_creacion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )
