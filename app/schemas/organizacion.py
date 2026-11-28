from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.catalogo import AreaImpactoOut
from app.schemas.perfil import TIPOS_ORGANIZACION

AVISO_VERIFICACION = (
    "La insignia indica que la organización presentó documentación que fue revisada "
    "por Solari. No es una garantía absoluta de la calidad ni de la seguridad de sus "
    "actividades."
)


class PerfilPublicoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    historia: str | None = Field(default=None, max_length=3000)
    mision: str | None = Field(default=None, max_length=2000)
    areas: list[int] | None = Field(default=None, max_length=15)
    mostrar_telefono: bool | None = None
    mostrar_correo: bool | None = None
    mostrar_direccion: bool | None = None
    tipo_organizacion: str | None = None

    @field_validator("tipo_organizacion")
    @classmethod
    def _tipo(cls, v: str | None) -> str | None:
        if v is not None and v not in TIPOS_ORGANIZACION:
            raise ValueError(f"tipo_organizacion debe ser uno de {TIPOS_ORGANIZACION}")
        return v


class EstadisticasOrganizacion(BaseModel):
    """Calculadas con registros reales (R11): no se confunden actividades publicadas
    con realizadas, ni postulaciones con participaciones efectivas."""

    antiguedad_dias: int
    convocatorias_creadas: int
    individuales_realizadas: int
    individuales_canceladas: int
    recurrentes_realizadas: int
    recurrentes_canceladas: int
    voluntarios_participantes: int
    participaciones_confirmadas: int


class VerificacionPublica(BaseModel):
    verificada: bool
    fecha: datetime | None = None
    aviso: str = AVISO_VERIFICACION


class ContactoPublico(BaseModel):
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None
    pagina_web: str | None = None


class GaleriaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ruta: str
    descripcion: str | None = None


class ResumenResenas(BaseModel):
    promedio: float | None = None
    total: int = 0


class ResenaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calificacion: int = Field(ge=1, le=5)
    comentario: str = Field(min_length=10, max_length=1000)


class ResenaRespuesta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    respuesta: str = Field(min_length=3, max_length=1000)


class ResenaOut(BaseModel):
    id: uuid.UUID
    voluntario_nombre: str
    calificacion: int
    comentario: str
    respuesta: str | None = None
    fecha_respuesta: datetime | None = None
    fecha_creacion: datetime
    estado: str = "VISIBLE"


class ResenasPage(BaseModel):
    data: list[ResenaOut]
    total: int
    page: int
    per_page: int
    pages: int
    resumen: ResumenResenas


class OrganizacionPublicaOut(BaseModel):
    id: uuid.UUID
    nombre: str
    tipo_organizacion: str
    constituida_legalmente: bool
    logo: str | None = None
    imagen_banner: str | None = None
    descripcion: str
    historia: str | None = None
    mision: str | None = None
    municipio: str | None = None
    areas: list[AreaImpactoOut] = []
    contacto: ContactoPublico
    galeria: list[GaleriaItem] = []
    estadisticas: EstadisticasOrganizacion
    verificacion: VerificacionPublica
    resenas: ResumenResenas
    es_mia: bool = False
    es_favorita: bool = False
    puede_resenar: bool = False
    mi_resena: ResenaOut | None = None


class DocumentoVerifOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_documento: str
    nombre_original: str
    ruta_archivo: str
    validado: bool
    fecha_subida: datetime


class VerificacionEstadoOut(BaseModel):
    estado: str
    nota: str | None = None
    fecha: datetime | None = None
    documentos: list[DocumentoVerifOut] = []
    aviso: str = AVISO_VERIFICACION
