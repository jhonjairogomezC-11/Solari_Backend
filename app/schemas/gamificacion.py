from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ─────────────── Intereses ───────────────

class InteresOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class InteresesInput(BaseModel):
    """Selección de intereses del voluntario (entre 1 y 15; ideal 10)."""
    model_config = ConfigDict(extra="forbid")
    interes_ids: list[int] = Field(min_length=1, max_length=15)


# ─────────────── Logros ───────────────

class LogroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    nombre: str
    descripcion: str
    icono: str | None = None
    tipo: str
    umbral: int


class LogroEstadoOut(LogroOut):
    """Logro con el estado de desbloqueo para un voluntario."""
    desbloqueado: bool = False
    fecha_obtencion: datetime | None = None


# ─────────────── Puntos / XP ───────────────

class TransaccionXpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    puntos_total: int
    motivo: str
    fecha: datetime


class ResumenGamificacion(BaseModel):
    xp_total: int
    xp_saldo: int
    horas_acumuladas: int
    actividades_completadas: int
    logros_desbloqueados: int
    logros_totales: int
    # Nivel visual (no desbloquea funcionalidades).
    nivel: int = 1
    nivel_nombre: str = "Chispa"
    xp_nivel_actual: int = 0
    xp_siguiente_nivel: int | None = None


# ─────────────── Ranking ───────────────

class RankingItem(BaseModel):
    posicion: int
    voluntario_id: uuid.UUID
    nombre: str
    foto_perfil: str | None = None
    xp: int
    nivel: int = 1


class RankingResponse(BaseModel):
    top: list[RankingItem]
    mi_posicion: int  # 0 = sin puntos / fuera de ranking
    mi_xp: int
    total_voluntarios: int
    en_top: bool
