"""Modelos ORM de las tablas de tokens existentes.

Las tablas `refresh_tokens`, `recuperacion_password` y `verificacion_email` fueron
creadas por Laravel con una columna `token` en texto plano. La migración Alembic
`0001` añade una columna aditiva `token_hash` (nullable) para que el backend
Python almacene SOLO el hash SHA-256. La columna `token` se mantiene nullable
durante la coexistencia para no romper a Laravel.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expiracion: Mapped[datetime] = mapped_column()
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_uso: Mapped[datetime | None] = mapped_column(nullable=True)
    ip_solicitud: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))


class RecuperacionPassword(Base):
    __tablename__ = "recuperacion_password"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expiracion: Mapped[datetime] = mapped_column()
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_uso: Mapped[datetime | None] = mapped_column(nullable=True)
    intentos: Mapped[int | None] = mapped_column(nullable=True, default=0)
    ip_solicitud: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))


class VerificacionEmail(Base):
    __tablename__ = "verificacion_email"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expiracion: Mapped[datetime] = mapped_column()
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
