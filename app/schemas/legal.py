"""Esquemas Pydantic de documentos legales."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentoLegalVigenteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nombre: str
    descripcion: str | None = None
    requerido_registro: bool
    version: str
    version_id: int
    url_publica: str | None = None
    contenido: str | None = None
    fecha_publicacion: datetime
