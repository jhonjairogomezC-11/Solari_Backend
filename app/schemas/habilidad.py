from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HabilidadesInput(BaseModel):
    """Selección de habilidades. El rango 3-10 se valida en el servicio (R3)."""

    model_config = ConfigDict(extra="forbid")
    habilidad_ids: list[int] = Field(max_length=50)
