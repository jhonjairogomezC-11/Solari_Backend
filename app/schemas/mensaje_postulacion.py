from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_LONGITUD_MENSAJE = 1000


class MensajePostulacionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mensaje: str = Field(min_length=1, max_length=MAX_LONGITUD_MENSAJE)

    @field_validator("mensaje")
    @classmethod
    def _no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El mensaje no puede estar vacío.")
        return v


class MensajePostulacionOut(BaseModel):
    id: uuid.UUID
    autor_rol: str
    autor_nombre: str
    mensaje: str
    leido: bool
    fecha_creacion: datetime
    es_mio: bool


class ConversacionPostulacionOut(BaseModel):
    postulacion_id: uuid.UUID
    estado: str
    puede_escribir: bool
    convocatoria_titulo: str
    contraparte_nombre: str
    mensajes: list[MensajePostulacionOut]


class NoLeidosOut(BaseModel):
    total: int
