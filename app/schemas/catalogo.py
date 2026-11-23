from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DepartamentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class MunicipioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    departamento: DepartamentoOut | None = None


class AreaImpactoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class HabilidadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    categoria: str | None = None
    es_profesional: bool = False
