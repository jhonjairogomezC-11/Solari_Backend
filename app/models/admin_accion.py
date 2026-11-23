"""Auditoría administrativa (tabla `admin_acciones`, ya existente).

Cada acción sensible del panel admin deja un registro: quién, qué, sobre qué
objeto, valores antes/después y motivo.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ACCIONES_NUEVAS = (
    "SOPORTE_RESPONDIDO",
    "SOLICITUD_CUENTA_RESUELTA",
    "USUARIO_ANONIMIZADO",
    "VERIFICACION_DOCUMENTAL_RESUELTA",
    "RESENA_MODERADA",
    "VOLUNTARIO_VERIFICADO",
    "CATALOGO_MODIFICADO",
)

_tipo_accion = ENUM(
    "USUARIO_SUSPENDIDO", "USUARIO_BLOQUEADO", "USUARIO_REACTIVADO", "USUARIO_ELIMINADO",
    "USUARIO_EDITADO", "FUNDACION_APROBADA", "FUNDACION_RECHAZADA", "FUNDACION_SUSPENDIDA",
    "FUNDACION_REACTIVADA", "PUBLICACION_OCULTADA", "PUBLICACION_RESTAURADA",
    "PUBLICACION_ELIMINADA", "PUBLICACION_ESTADO_CAMBIADO", "POSTULACION_INTERVENIDA",
    "REPORTE_RESUELTO", "REPORTE_DESESTIMADO", "PUNTOS_AJUSTADOS", "LOGRO_ASIGNADO",
    "ADMIN_CREADO", "ADMIN_DESACTIVADO", "ADMIN_PERMISOS_ACTUALIZADOS",
    *ACCIONES_NUEVAS,
    name="tipo_accion_admin",
    create_type=False,
)


class AdminPerfil(Base):
    """Perfil de administrador (tabla existente). Solo se mapean las columnas usadas.

    `admin_acciones` y `historial_estados_voluntario` referencian ESTE id, no el de
    `usuarios`; por eso la auditoría resuelve el perfil a partir del usuario.
    """

    __tablename__ = "admin_perfiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True
    )
    activo: Mapped[bool] = mapped_column(default=True)


class AdminAccion(Base):
    __tablename__ = "admin_acciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_perfiles.id", ondelete="RESTRICT")
    )
    tipo: Mapped[str] = mapped_column(_tipo_accion)
    objeto_tipo: Mapped[str | None] = mapped_column(String, nullable=True)
    objeto_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    objeto_descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    detalle_anterior: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    detalle_nuevo: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_accion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))


class HistorialEstadoVoluntario(Base):
    """Historial de cambios de estado de cuenta (tabla ya existente)."""

    __tablename__ = "historial_estados_voluntario"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    estado_anterior: Mapped[str] = mapped_column(String)
    estado_nuevo: Mapped[str] = mapped_column(String)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_perfiles.id", ondelete="RESTRICT")
    )
    fecha: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
