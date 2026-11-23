"""Modelo ORM de la tabla existente `voluntarios`."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_tipo_doc_enum = ENUM(
    "CC", "TI", "CE", "PASAPORTE", name="tipo_documento", create_type=False
)
_genero_enum = ENUM("MASCULINO", "FEMENINO", "OTRO", name="genero_tipo", create_type=False)
_disp_enum = ENUM(
    "ENTRE_SEMANA", "FINES_DE_SEMANA", "FLEXIBLE", name="disponibilidad_tipo", create_type=False
)


class Voluntario(Base):
    __tablename__ = "voluntarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True
    )
    tipo_documento: Mapped[str] = mapped_column(_tipo_doc_enum)
    numero_documento: Mapped[str] = mapped_column(String(30), unique=True)
    documento_identidad: Mapped[str | None] = mapped_column(String, nullable=True)
    esta_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    genero: Mapped[str] = mapped_column(_genero_enum)
    municipio_id: Mapped[int] = mapped_column(Integer)
    disponibilidad: Mapped[str] = mapped_column(_disp_enum)
    experiencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    foto_perfil: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # ── Campos de perfil ampliado (aditivos, todos nullable) ──
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    telefono_contacto: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nivel_educativo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profesion: Mapped[str | None] = mapped_column(String(150), nullable=True)
    idiomas: Mapped[str | None] = mapped_column(String(300), nullable=True)
    preferencia_modalidad: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contacto_emergencia_nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contacto_emergencia_telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # ── Estadísticas de trayectoria (aditivas, con default) ──
    # Los puntos (XP) viven en `voluntario_puntos`; aquí solo cacheamos horas y
    # actividades completadas para lecturas rápidas de perfil/ranking.
    horas_acumuladas: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    actividades_completadas: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
