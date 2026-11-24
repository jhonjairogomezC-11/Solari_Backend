"""Esquemas de salida del calendario de actividades y de los recordatorios."""

from __future__ import annotations

import uuid
from datetime import date, time

from pydantic import BaseModel


class EventoCalendario(BaseModel):
    """Una actividad en el calendario del voluntario o de la organización."""

    publicacion_id: uuid.UUID
    # Solo en el calendario del voluntario.
    postulacion_id: uuid.UUID | None = None
    estado_postulacion: str | None = None
    # True si la participación está aceptada; False si aún está pendiente,
    # en revisión o en lista de espera.
    confirmada: bool = True
    titulo: str
    fecha_inicio: date
    fecha_fin: date
    hora_inicio: time | None = None
    hora_fin: time | None = None
    modalidad: str
    municipio: str | None = None
    # Dirección y enlace solo se entregan al voluntario aceptado (y a la organización).
    direccion_exacta: str | None = None
    enlace_virtual: str | None = None
    horas_reconocidas: int = 0
    organizacion_id: uuid.UUID
    organizacion: str
    # Solo en el calendario de la organización.
    cupo_maximo: int | None = None
    voluntarios_aceptados: int | None = None


class RecordatoriosResultado(BaseModel):
    creados: int
