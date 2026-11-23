"""Modelos de preferencias de notificación y auditoría de cambios sensibles.

Tablas NUEVAS y aditivas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PreferenciasNotificacion(Base):
    """Preferencias de notificación por usuario (1:1)."""

    __tablename__ = "preferencias_notificacion"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    notif_postulaciones: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_convocatorias: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_recordatorios: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_logros: Mapped[bool] = mapped_column(Boolean, default=True)
    notif_soporte: Mapped[bool] = mapped_column(Boolean, default=True)
    canal_email: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )


class AuditoriaPerfil(Base):
    """Registro de cambios en campos sensibles del perfil (inmutables)."""

    __tablename__ = "auditoria_perfil"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    campo: Mapped[str] = mapped_column(String(60))
    valor_anterior: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_nuevo: Mapped[str | None] = mapped_column(Text, nullable=True)
    realizado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )
