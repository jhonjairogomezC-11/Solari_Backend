from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.catalogo import HabilidadOut

MODALIDADES = ("PRESENCIAL", "VIRTUAL", "HIBRIDA")
DIFICULTADES = ("FACIL", "MEDIA", "DIFICIL", "MUY_DIFICIL")
ESTADOS_PUB = (
    "BORRADOR", "PENDIENTE_APROBACION", "PUBLICADA",
    "CERRADA", "CANCELADA", "COMPLETADA", "FINALIZADA",
)


class FundacionResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    logo: str | None = None
    verificada: bool = False
    tipo_organizacion: str = "FUNDACION"


class PublicacionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(min_length=10)
    categoria_id: int = Field(gt=0)
    modalidad: str
    municipio_id: int | None = None
    direccion_exacta: str | None = Field(default=None, max_length=200)
    enlace_virtual: str | None = None
    fecha_inicio: date
    fecha_fin: date
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cupo_maximo: int = Field(default=1, ge=1)
    edad_minima: int | None = Field(default=None, ge=14)
    edad_maxima: int | None = None
    requisitos_adicionales: str | None = None
    contacto_nombre: str | None = Field(default=None, max_length=150)
    contacto_email: str | None = Field(default=None, max_length=150)
    contacto_telefono: str | None = Field(default=None, max_length=20)
    # ── Campos ricos ──
    objetivo: str | None = None
    impacto_esperado: str | None = None
    actividades_voluntario: str | None = None
    perfil_beneficiarios: str | None = None
    que_llevar: str | None = None
    recomendaciones: str | None = None
    incluye_transporte: bool = False
    incluye_alimentacion: bool = False
    incluye_seguro: bool = False
    politica_cancelacion: str | None = None
    otorga_certificado: bool = False
    horas_reconocidas: int = Field(default=0, ge=0, le=10000)
    nivel_experiencia: str | None = Field(default=None, max_length=40)
    fecha_limite_postulacion: date | None = None
    dificultad: str = "FACIL"
    urgente: bool = False
    # R3: una actividad exige entre 3 y 10 habilidades (se exige al publicar).
    habilidades: list[int] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validar_campos(self) -> PublicacionCreate:
        if self.modalidad not in MODALIDADES:
            raise ValueError(f"modalidad debe ser uno de {MODALIDADES}")
        if self.dificultad not in DIFICULTADES:
            raise ValueError(f"dificultad debe ser una de {DIFICULTADES}")
        if self.modalidad in ("PRESENCIAL", "HIBRIDA") and not self.municipio_id:
            raise ValueError("municipio_id es obligatorio para modalidad PRESENCIAL o HIBRIDA.")
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin debe ser mayor o igual a fecha_inicio.")
        if self.edad_minima and self.edad_maxima and self.edad_maxima < self.edad_minima:
            raise ValueError("edad_maxima debe ser mayor o igual a edad_minima.")
        if (
            self.fecha_limite_postulacion
            and self.fecha_limite_postulacion > self.fecha_inicio
        ):
            raise ValueError(
                "La fecha límite de postulación no puede ser posterior al inicio."
            )
        return self


class PublicacionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = None
    categoria_id: int | None = Field(default=None, gt=0)
    modalidad: str | None = None
    municipio_id: int | None = None
    direccion_exacta: str | None = Field(default=None, max_length=200)
    enlace_virtual: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cupo_maximo: int | None = Field(default=None, ge=1)
    edad_minima: int | None = Field(default=None, ge=14)
    edad_maxima: int | None = None
    requisitos_adicionales: str | None = None
    contacto_nombre: str | None = Field(default=None, max_length=150)
    contacto_email: str | None = Field(default=None, max_length=150)
    contacto_telefono: str | None = Field(default=None, max_length=20)
    # ── Campos ricos (opcionales en update) ──
    objetivo: str | None = None
    impacto_esperado: str | None = None
    actividades_voluntario: str | None = None
    perfil_beneficiarios: str | None = None
    que_llevar: str | None = None
    recomendaciones: str | None = None
    incluye_transporte: bool | None = None
    incluye_alimentacion: bool | None = None
    incluye_seguro: bool | None = None
    politica_cancelacion: str | None = None
    otorga_certificado: bool | None = None
    horas_reconocidas: int | None = Field(default=None, ge=0, le=10000)
    nivel_experiencia: str | None = Field(default=None, max_length=40)
    fecha_limite_postulacion: date | None = None
    dificultad: str | None = None
    urgente: bool | None = None
    habilidades: list[int] | None = Field(default=None, max_length=10)

    @model_validator(mode="after")
    def validar_campos(self) -> PublicacionUpdate:
        if self.modalidad and self.modalidad not in MODALIDADES:
            raise ValueError(f"modalidad debe ser uno de {MODALIDADES}")
        if self.dificultad and self.dificultad not in DIFICULTADES:
            raise ValueError(f"dificultad debe ser una de {DIFICULTADES}")
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin debe ser mayor o igual a fecha_inicio.")
        return self


class PublicacionImagenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ruta: str
    orden: int = 0


class PublicacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    descripcion: str
    modalidad: str
    estado: str
    fecha_inicio: date
    fecha_fin: date
    hora_inicio: time | None = None
    hora_fin: time | None = None
    cupo_maximo: int
    edad_minima: int | None = None
    edad_maxima: int | None = None
    requisitos_adicionales: str | None = None
    direccion_exacta: str | None = None
    enlace_virtual: str | None = None
    imagen: str | None = None
    contacto_nombre: str | None = None
    contacto_email: str | None = None
    contacto_telefono: str | None = None
    # ── Campos ricos ──
    objetivo: str | None = None
    impacto_esperado: str | None = None
    actividades_voluntario: str | None = None
    perfil_beneficiarios: str | None = None
    que_llevar: str | None = None
    recomendaciones: str | None = None
    incluye_transporte: bool = False
    incluye_alimentacion: bool = False
    incluye_seguro: bool = False
    politica_cancelacion: str | None = None
    otorga_certificado: bool = False
    horas_reconocidas: int = 0
    nivel_experiencia: str | None = None
    fecha_limite_postulacion: date | None = None
    dificultad: str = "FACIL"
    urgente: bool = False
    fecha_publicacion: datetime | None = None
    fecha_creacion: datetime
    fundacion_id: uuid.UUID
    categoria_id: int
    municipio_id: int | None = None
    programacion_id: uuid.UUID | None = None
    habilidades: list[HabilidadOut] = []
    imagenes: list[PublicacionImagenOut] = []
    # Solo en las vistas de la propia organización.
    postulaciones_total: int | None = None
    postulaciones_pendientes: int | None = None
    # Personalización para el voluntario autenticado (None si no aplica).
    coincidencia: int | None = None
    habilidades_coinciden: list[int] = []
    fundacion: FundacionResumen | None = None


class PublicacionConRelaciones(PublicacionOut):
    """Versión con relaciones resueltas (para detalle y listados ricos)."""
    habilidades: list[HabilidadOut] = []


class PaginatedResponse[T](BaseModel):
    data: list[T]
    total: int
    page: int
    per_page: int
    pages: int
