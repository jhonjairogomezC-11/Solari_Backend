"""Habilidades del voluntario (tabla `voluntario_habilidades`, ya existente)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Reglas R3: entre 3 y 10 habilidades por voluntario y por actividad.
MIN_HABILIDADES = 3
MAX_HABILIDADES = 10


class VoluntarioHabilidad(Base):
    __tablename__ = "voluntario_habilidades"

    voluntario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voluntarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    habilidad_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("habilidades.id", ondelete="CASCADE"), primary_key=True
    )
