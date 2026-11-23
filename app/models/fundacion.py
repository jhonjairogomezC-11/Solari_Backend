"""Modelo ORM de la tabla existente `fundaciones`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, text
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
    # NIT y documento legal son opcionales: pueden participar organizaciones sin
    # constitución legal (refugios independientes, colectivos). Regla R13.
    nit: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    representante_legal: Mapped[str] = mapped_column(String(150))
    correo_institucional: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telefono: Mapped[str] = mapped_column(String(20))
    direccion: Mapped[str] = mapped_column(String(200))
    municipio_id: Mapped[int] = mapped_column(Integer)
    pagina_web: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descripcion: Mapped[str] = mapped_column(Text)
    documento_legal: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # ── Perfil público y verificación documental (aditivos) ──
    tipo_organizacion: Mapped[str] = mapped_column(
        String(30), default="FUNDACION", server_default=text("'FUNDACION'")
    )
    constituida_legalmente: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    historia: Mapped[str | None] = mapped_column(Text, nullable=True)
    mision: Mapped[str | None] = mapped_column(Text, nullable=True)
    mostrar_telefono: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    mostrar_correo: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    mostrar_direccion: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    # NO_SOLICITADA | EN_REVISION | INFO_REQUERIDA | VERIFICADA | RECHAZADA | REVOCADA
    verificacion_documental: Mapped[str] = mapped_column(
        String(30), default="NO_SOLICITADA", server_default=text("'NO_SOLICITADA'")
    )
    verificacion_documental_fecha: Mapped[datetime | None] = mapped_column(nullable=True)
    verificacion_documental_nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    verificacion_documental_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    estado_verificacion: Mapped[str] = mapped_column(
        _estado_verif_enum, default=ESTADO_PENDIENTE
    )
    fecha_verificacion: Mapped[datetime | None] = mapped_column(nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
