"""Perfil público de la organización: galería, documentos de verificación y reseñas.

`fundacion_documentos` y `fundacion_areas` ya existían (Laravel); se mapean aquí.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

TIPOS_ORGANIZACION = ("FUNDACION", "REFUGIO", "COLECTIVO", "INICIATIVA_CIUDADANA", "OTRA")
TIPOS_DOCUMENTO_VERIF = (
    "CERTIFICADO_EXISTENCIA", "RUT", "NATURALEZA_JURIDICA", "OTRO",
)

# Estados de la verificación documental (opcional, distinta de la aprobación de cuenta).
VD_NO_SOLICITADA = "NO_SOLICITADA"
VD_EN_REVISION = "EN_REVISION"
VD_INFO_REQUERIDA = "INFO_REQUERIDA"
VD_VERIFICADA = "VERIFICADA"
VD_RECHAZADA = "RECHAZADA"
VD_REVOCADA = "REVOCADA"

RESENA_VISIBLE = "VISIBLE"
RESENA_PENDIENTE = "PENDIENTE_MODERACION"
RESENA_OCULTA = "OCULTA"

fundacion_areas = Table(
    "fundacion_areas",
    Base.metadata,
    Column(
        "fundacion_id",
        UUID(as_uuid=True),
        ForeignKey("fundaciones.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "area_id",
        Integer,
        ForeignKey("areas_impacto.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class FundacionDocumento(Base):
    """Documento privado de verificación (certificado, RUT, etc.)."""

    __tablename__ = "fundacion_documentos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fundacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fundaciones.id", ondelete="CASCADE")
    )
    tipo_documento: Mapped[str] = mapped_column(String)
    nombre_original: Mapped[str] = mapped_column(String)
    ruta_archivo: Mapped[str] = mapped_column(Text)
    validado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_subida: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))


class FundacionGaleria(Base):
    __tablename__ = "fundacion_galeria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fundacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fundaciones.id", ondelete="CASCADE")
    )
    ruta: Mapped[str] = mapped_column(String(500))
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contiene_menores: Mapped[bool] = mapped_column(Boolean, default=False)
    # Control de protección de imagen: obligatoria cuando aparezcan menores o
    # personas en situación de vulnerabilidad.
    autorizacion_imagen: Mapped[bool] = mapped_column(Boolean, default=False)
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))


class ResenaOrganizacion(Base):
    """Reseña de un voluntario con participación confirmada (R12)."""

    __tablename__ = "resenas_organizacion"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fundacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fundaciones.id", ondelete="CASCADE")
    )
    voluntario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voluntarios.id", ondelete="CASCADE")
    )
    calificacion: Mapped[int] = mapped_column(SmallInteger)
    comentario: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(30), default=RESENA_VISIBLE)
    motivo_moderacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    respuesta: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_respuesta: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
