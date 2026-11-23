from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.programacion import UNIDADES


class ProgramacionCreate(BaseModel):
    """Configura una necesidad periódica (p. ej. limpieza de un refugio cada 3 días)."""

    model_config = ConfigDict(extra="forbid")

    unidad_intervalo: str
    intervalo: int = Field(ge=1, le=365)
    fecha_inicio: date
    duracion_dias: int = Field(default=1, ge=1, le=30)
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cupo_maximo: int = Field(ge=1, le=1000)
    # Campos de la convocatoria que se repiten (título, descripción, categoría,
    # modalidad, municipio, habilidades, etc.). Se validan con PublicacionCreate.
    plantilla: dict[str, Any]

    @field_validator("unidad_intervalo")
    @classmethod
    def _unidad(cls, v: str) -> str:
        if v not in UNIDADES:
            raise ValueError(f"unidad_intervalo debe ser una de {UNIDADES}")
        return v


class ConvocatoriaGenerada(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fecha_inicio: date
    fecha_fin: date
    estado: str


class ProgramacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    unidad_intervalo: str
    intervalo: int
    fecha_inicio: date
    duracion_dias: int
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cupo_maximo: int
    estado: str
    total_generadas: int
    ciclo_generadas: int
    proxima_fecha: date
    fecha_pausa: datetime | None = None
    fecha_creacion: datetime
    convocatorias: list[ConvocatoriaGenerada] = []
