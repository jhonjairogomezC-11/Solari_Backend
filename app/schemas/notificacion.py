from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: str
    mensaje: str
    objeto_tipo: str | None = None
    objeto_id: uuid.UUID | None = None
    leida: bool
    fecha_lectura: datetime | None = None
    fecha_creacion: datetime
