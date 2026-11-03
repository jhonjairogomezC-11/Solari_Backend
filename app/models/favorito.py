"""Modelo ORM de la tabla `voluntario_favoritos`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

TIPO_PUBLICACION = "PUBLICACION"
TIPO_FUNDACION = "FUNDACION"


class VoluntarioFavorito(Base):
    __tablename__ = "voluntario_favoritos"

    # La tabla no tiene default en la BD (Laravel genera el UUID en la app).
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    voluntario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voluntarios.id", ondelete="CASCADE")
    )
    tipo: Mapped[str] = mapped_column(String(20))
    publicacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publicaciones.id", ondelete="CASCADE"), nullable=True
    )
    fundacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fundaciones.id", ondelete="CASCADE"), nullable=True
    )
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
