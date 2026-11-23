"""Programaciones de actividades recurrentes.

Regla R4: una programación genera como máximo tres convocatorias consecutivas y
queda PAUSADA hasta que la organización autorice de forma explícita un nuevo
ciclo. El silencio no equivale a continuar.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, ForeignKey, Integer, String, Time, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

UNIDAD_DIAS = "DIAS"
UNIDAD_SEMANAS = "SEMANAS"
UNIDAD_MESES = "MESES"
UNIDADES = (UNIDAD_DIAS, UNIDAD_SEMANAS, UNIDAD_MESES)

PROG_ACTIVA = "ACTIVA"
PROG_PAUSADA = "PAUSADA"
PROG_TERMINADA = "TERMINADA"

MAX_POR_CICLO = 3


class ProgramacionRecurrente(Base):
    __tablename__ = "programaciones_recurrentes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fundacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fundaciones.id", ondelete="CASCADE")
    )
    titulo: Mapped[str] = mapped_column(String(200))
    # Campos de la convocatoria que se repiten (descripción, categoría, modalidad,
    # municipio, habilidades, etc.). Las fechas las calcula la programación.
    plantilla: Mapped[dict] = mapped_column(JSONB)
    unidad_intervalo: Mapped[str] = mapped_column(String(10))
    intervalo: Mapped[int] = mapped_column(Integer)
    fecha_inicio: Mapped[date] = mapped_column(Date)
    duracion_dias: Mapped[int] = mapped_column(Integer, default=1)
    hora_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_fin: Mapped[time | None] = mapped_column(Time, nullable=True)
    cupo_maximo: Mapped[int] = mapped_column(Integer, default=1)
    estado: Mapped[str] = mapped_column(String(20), default=PROG_ACTIVA)
    total_generadas: Mapped[int] = mapped_column(Integer, default=0)
    ciclo_generadas: Mapped[int] = mapped_column(Integer, default=0)
    proxima_fecha: Mapped[date] = mapped_column(Date)
    fecha_pausa: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP")
    )
