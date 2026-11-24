from __future__ import annotations

import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.ofrecimiento import (
    CATEGORIAS_OBJETO,
    CATEGORIAS_SERVICIO,
    ESTADOS_PRODUCTO,
    MODALIDADES_ENTREGA,
    MODALIDADES_SERVICIO,
    TIPO_OBJETO,
    TIPOS_OFRECIMIENTO,
)
from app.schemas.catalogo import HabilidadOut

# R1: las publicaciones son gratuitas; no hay compraventa ni pagos en la plataforma.
_RE_COMERCIAL = re.compile(
    r"(\$\s?\d|\bprecio\b|\bvendo\b|\bventa\b|\bcobro\b|\bcobrar\b|\bpesos\b|\bcop\b|\bpago\b)",
    re.IGNORECASE,
)


class OfrecimientoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: str
    titulo: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(min_length=10, max_length=2000)
    categoria: str
    cantidad_total: int = Field(default=1, ge=1, le=10000)
    estado_producto: str | None = None
    modalidad_entrega: str | None = None
    municipio_id: int | None = Field(default=None, gt=0)
    fecha_vencimiento: date | None = None
    disponibilidad: str | None = Field(default=None, max_length=500)
    alcance: str | None = Field(default=None, max_length=1000)
    condiciones: str | None = Field(default=None, max_length=1000)
    habilidades: list[int] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validar(self) -> OfrecimientoCreate:
        if self.tipo not in TIPOS_OFRECIMIENTO:
            raise ValueError(f"tipo debe ser uno de {TIPOS_OFRECIMIENTO}")
        for texto in (self.titulo, self.descripcion, self.condiciones or ""):
            if _RE_COMERCIAL.search(texto):
                raise ValueError(
                    "Las publicaciones deben ser gratuitas: no incluyas precios, ventas ni cobros."
                )
        if self.tipo == TIPO_OBJETO:
            if self.categoria not in CATEGORIAS_OBJETO:
                raise ValueError(f"categoria de objeto debe ser una de {CATEGORIAS_OBJETO}")
            if self.estado_producto not in ESTADOS_PRODUCTO:
                raise ValueError(f"estado_producto debe ser uno de {ESTADOS_PRODUCTO}")
            if self.modalidad_entrega not in MODALIDADES_ENTREGA:
                raise ValueError(f"modalidad_entrega debe ser una de {MODALIDADES_ENTREGA}")
            if self.municipio_id is None:
                raise ValueError("Indica el municipio donde está el objeto.")
        else:
            if self.categoria not in CATEGORIAS_SERVICIO:
                raise ValueError(f"categoria de servicio debe ser una de {CATEGORIAS_SERVICIO}")
            if self.modalidad_entrega not in MODALIDADES_SERVICIO:
                raise ValueError(f"modalidad del servicio debe ser una de {MODALIDADES_SERVICIO}")
            if not self.habilidades:
                raise ValueError("Un servicio debe indicar al menos una habilidad del catálogo.")
            if self.modalidad_entrega == "PRESENCIAL" and self.municipio_id is None:
                raise ValueError("Un servicio presencial debe indicar el municipio.")
            self.cantidad_total = 1  # un servicio se presta una vez
        if self.fecha_vencimiento and self.fecha_vencimiento < date.today():
            raise ValueError("La fecha de vencimiento no puede estar en el pasado.")
        return self


class OfrecimientoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, min_length=10, max_length=2000)
    cantidad_total: int | None = Field(default=None, ge=1, le=10000)
    estado_producto: str | None = None
    modalidad_entrega: str | None = None
    municipio_id: int | None = Field(default=None, gt=0)
    fecha_vencimiento: date | None = None
    disponibilidad: str | None = Field(default=None, max_length=500)
    alcance: str | None = Field(default=None, max_length=1000)
    condiciones: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validar(self) -> OfrecimientoUpdate:
        for texto in (self.titulo or "", self.descripcion or "", self.condiciones or ""):
            if _RE_COMERCIAL.search(texto):
                raise ValueError(
                    "Las publicaciones deben ser gratuitas: no incluyas precios, ventas ni cobros."
                )
        if self.estado_producto and self.estado_producto not in ESTADOS_PRODUCTO:
            raise ValueError(f"estado_producto debe ser uno de {ESTADOS_PRODUCTO}")
        return self


class OfrecimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: str
    titulo: str
    descripcion: str
    categoria: str
    cantidad_total: int
    cantidad_disponible: int
    estado_producto: str | None = None
    modalidad_entrega: str | None = None
    municipio_id: int | None = None
    municipio: str | None = None
    fecha_vencimiento: date | None = None
    disponibilidad: str | None = None
    alcance: str | None = None
    condiciones: str | None = None
    imagenes: list[str] = []
    estado: str
    fecha_creacion: datetime
    # Solo el primer nombre del voluntario: no se exponen datos personales.
    voluntario_nombre: str | None = None
    habilidades: list[HabilidadOut] = []
    es_mio: bool = False
    solicitudes_pendientes: int | None = None
    # True si la fundación autenticada ya tiene una solicitud en curso.
    ya_solicitado: bool = False


class OfrecimientoPage(BaseModel):
    data: list[OfrecimientoOut]
    total: int
    page: int
    per_page: int
    pages: int


class SolicitudInteresCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cantidad: int = Field(default=1, ge=1, le=10000)
    mensaje: str | None = Field(default=None, max_length=500)


class ResponderSolicitud(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str

    @model_validator(mode="after")
    def validar(self) -> ResponderSolicitud:
        if self.decision not in ("ACEPTAR", "RECHAZAR"):
            raise ValueError("decision debe ser ACEPTAR o RECHAZAR")
        return self


class SolicitudInteresOut(BaseModel):
    id: uuid.UUID
    ofrecimiento_id: uuid.UUID
    ofrecimiento_titulo: str
    ofrecimiento_tipo: str
    fundacion_id: uuid.UUID
    fundacion_nombre: str
    voluntario_nombre: str
    cantidad: int
    mensaje: str | None = None
    estado: str
    confirmada_voluntario: bool
    confirmada_fundacion: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    fecha_completada: datetime | None = None
    soy_voluntario: bool = False


class MensajeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mensaje: str = Field(min_length=1, max_length=1000)


class MensajeOut(BaseModel):
    id: uuid.UUID
    autor_rol: str
    autor_nombre: str
    mensaje: str
    fecha_creacion: datetime
    es_mio: bool


class CategoriasOfrecimiento(BaseModel):
    objetos: list[str]
    servicios: list[str]
    estados_producto: list[str]
    modalidades_entrega: list[str]
    modalidades_servicio: list[str]
