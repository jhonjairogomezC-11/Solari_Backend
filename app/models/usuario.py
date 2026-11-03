"""Modelo ORM de la tabla existente `usuarios` (creada por Laravel).

No se renombra ninguna columna. Los enums se mapean como texto porque PostgreSQL
usa tipos ENUM nativos y SQLAlchemy los lee como strings.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Tipos ENUM nativos ya existentes en PostgreSQL (create_type=False: no los crea).
_rol_enum = ENUM(
    "VOLUNTARIO", "FUNDACION", "ADMIN", name="rol_usuario", create_type=False
)
_estado_enum = ENUM(
    "ACTIVO", "BLOQUEADO", "SUSPENDIDO", name="estado_usuario", create_type=False
)
_provider_enum = ENUM("LOCAL", "GOOGLE", name="proveedor_auth", create_type=False)

ROL_VOLUNTARIO = "VOLUNTARIO"
ROL_FUNDACION = "FUNDACION"
ROL_ADMIN = "ADMIN"

ESTADO_ACTIVO = "ACTIVO"
ESTADO_BLOQUEADO = "BLOQUEADO"
ESTADO_SUSPENDIDO = "SUSPENDIDO"

PROVIDER_LOCAL = "LOCAL"
PROVIDER_GOOGLE = "GOOGLE"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(_provider_enum, default=PROVIDER_LOCAL)
    provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rol: Mapped[str] = mapped_column(_rol_enum)
    estado: Mapped[str] = mapped_column(_estado_enum, default=ESTADO_ACTIVO)
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_registro: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))

    @property
    def is_active(self) -> bool:
        return self.estado == ESTADO_ACTIVO
