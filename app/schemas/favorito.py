from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.publicacion import PublicacionOut


class FavoritoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: str
    publicacion_id: uuid.UUID | None = None
    fundacion_id: uuid.UUID | None = None
    fecha_creacion: datetime


class FavoritoConvocatoriaOut(BaseModel):
    """Favorito de convocatoria con la convocatoria embebida."""
    id: uuid.UUID
    fecha_creacion: datetime
    convocatoria: PublicacionOut


class ToggleResult(BaseModel):
    favorito: bool
