"""Modelos ORM para términos legales y aceptaciones (tablas NUEVAS, aditivas).

Diseño para cumplir el registro de evidencia de aceptación (Ley 1581/2012):
- `documentos_legales`: cada documento legal lógico (ej. TERMINOS, PRIVACIDAD).
- `documento_legal_versiones`: versiones publicadas de cada documento, con hash
  del contenido para integridad.
- `usuario_aceptaciones_legales`: qué versión aceptó cada usuario, cuándo, desde
  qué IP/user-agent. El cliente NO puede inventar versión ni fecha: el backend
  resuelve la versión vigente y sella la marca temporal del lado servidor.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Códigos de documento conocidos (extensible sin cambios de esquema).
DOC_TERMINOS = "TERMINOS_CONDICIONES"
DOC_PRIVACIDAD = "POLITICA_DATOS_PERSONALES"


class DocumentoLegal(Base):
    __tablename__ = "documentos_legales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(60), unique=True)
    nombre: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    requerido_registro: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))

    versiones: Mapped[list[DocumentoLegalVersion]] = relationship(
        back_populates="documento", cascade="all, delete-orphan"
    )


class DocumentoLegalVersion(Base):
    __tablename__ = "documento_legal_versiones"
    __table_args__ = (UniqueConstraint("documento_id", "version", name="uq_doc_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    documento_id: Mapped[int] = mapped_column(
        ForeignKey("documentos_legales.id", ondelete="CASCADE")
    )
    version: Mapped[str] = mapped_column(String(40))
    contenido: Mapped[str | None] = mapped_column(Text, nullable=True)
    contenido_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    url_publica: Mapped[str | None] = mapped_column(String(500), nullable=True)
    vigente: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_publicacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))

    documento: Mapped[DocumentoLegal] = relationship(back_populates="versiones")


class UsuarioAceptacionLegal(Base):
    __tablename__ = "usuario_aceptaciones_legales"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    version_id: Mapped[int] = mapped_column(
        ForeignKey("documento_legal_versiones.id", ondelete="RESTRICT")
    )
    aceptado: Mapped[bool] = mapped_column(Boolean, default=True)
    ip_aceptacion: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_aceptacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
