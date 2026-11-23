from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class PreferenciasOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    notif_postulaciones: bool
    notif_convocatorias: bool
    notif_recordatorios: bool
    notif_logros: bool
    notif_soporte: bool


class PreferenciasInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notif_postulaciones: bool = True
    notif_convocatorias: bool = True
    notif_recordatorios: bool = True
    notif_logros: bool = True
    notif_soporte: bool = True


# ─────────────── Trayectoria / historial ───────────────

class ActividadHistorial(BaseModel):
    postulacion_id: uuid.UUID
    publicacion_id: uuid.UUID
    titulo: str
    fundacion_nombre: str | None = None
    estado: str
    fecha_inicio: date | None = None
    horas_reconocidas: int = 0
    otorga_certificado: bool = False
    calificacion: int | None = None


class TrayectoriaOut(BaseModel):
    actividades_completadas: int
    horas_acumuladas: int
    xp_total: int
    fundaciones_colaboradas: int
    postulaciones_totales: int
    historial: list[ActividadHistorial]
