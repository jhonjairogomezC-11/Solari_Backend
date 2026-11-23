"""Schemas del panel de administración."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Dashboard / estadísticas
# ---------------------------------------------------------------------------


class ConteoPorEstado(BaseModel):
    estado: str
    total: int


class SerieTemporalPunto(BaseModel):
    fecha: date
    total: int


class DashboardStats(BaseModel):
    # Usuarios
    total_usuarios: int
    total_voluntarios: int
    total_fundaciones: int
    total_admins: int
    usuarios_activos: int
    usuarios_bloqueados: int
    usuarios_suspendidos: int
    nuevos_usuarios_30d: int
    # Fundaciones (verificación)
    fundaciones_pendientes: int
    fundaciones_aprobadas: int
    fundaciones_rechazadas: int
    # Convocatorias
    total_convocatorias: int
    convocatorias_publicadas: int
    convocatorias_borrador: int
    convocatorias_ocultas: int
    # Postulaciones
    total_postulaciones: int
    postulaciones_pendientes: int
    postulaciones_aceptadas: int
    # Series para gráficas
    registros_por_dia: list[SerieTemporalPunto] = []
    convocatorias_por_estado: list[ConteoPorEstado] = []
    postulaciones_por_estado: list[ConteoPorEstado] = []


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------


class AdminUsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    email: str
    rol: str
    estado: str
    provider: str
    telefono: str | None = None
    email_verificado: bool
    fecha_registro: datetime
    # Datos de perfil (si existen)
    tiene_perfil: bool = False
    perfil_id: uuid.UUID | None = None
    estado_verificacion_fundacion: str | None = None


class CambiarEstadoUsuario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: str = Field(description="ACTIVO | BLOQUEADO | SUSPENDIDO")
    motivo: str | None = Field(default=None, max_length=500)


class CambiarRolUsuario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rol: str = Field(description="VOLUNTARIO | FUNDACION | ADMIN")


# ---------------------------------------------------------------------------
# Fundaciones (verificación)
# ---------------------------------------------------------------------------


class AdminFundacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID
    nombre: str
    nit: str | None = None
    representante_legal: str
    correo_institucional: str | None = None
    telefono: str
    direccion: str
    municipio_id: int
    pagina_web: str | None = None
    descripcion: str
    documento_legal: str | None = None
    logo: str | None = None
    tipo_organizacion: str = "FUNDACION"
    constituida_legalmente: bool = True
    verificacion_documental: str = "NO_SOLICITADA"
    estado_verificacion: str
    fecha_verificacion: datetime | None = None
    motivo_rechazo: str | None = None
    fecha_creacion: datetime


class VerificarFundacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: str = Field(description="APROBADA | RECHAZADA | SUSPENDIDA | PENDIENTE")
    motivo: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Convocatorias (moderación)
# ---------------------------------------------------------------------------


class AdminConvocatoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    estado: str
    modalidad: str
    fecha_inicio: date
    fecha_fin: date
    cupo_maximo: int
    oculta_por_admin: bool
    motivo_ocultamiento: str | None = None
    fecha_creacion: datetime
    fundacion_id: uuid.UUID
    fundacion_nombre: str | None = None
    categoria_id: int
    total_postulaciones: int = 0


class OcultarConvocatoria(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ocultar: bool
    motivo: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Postulaciones (vista global)
# ---------------------------------------------------------------------------


class AdminPostulacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    estado: str
    fecha_postulacion: datetime
    publicacion_id: uuid.UUID
    publicacion_titulo: str | None = None
    voluntario_id: uuid.UUID
    voluntario_nombre: str | None = None


# ---------------------------------------------------------------------------
# Voluntarios (verificación de identidad)
# ---------------------------------------------------------------------------


class AdminVoluntarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID
    nombre: str | None = None
    email: str | None = None
    tipo_documento: str
    numero_documento: str
    foto_perfil: str | None = None
    documento_identidad: str | None = None
    esta_verificado: bool
    fecha_creacion: datetime


class VerificarVoluntario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verificado: bool


# ---------------------------------------------------------------------------
# Catálogos (CRUD)
# ---------------------------------------------------------------------------


class CatalogoItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=2, max_length=120)


class CatalogoItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=2, max_length=120)


class HabilidadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=2, max_length=100)
    categoria: str | None = Field(default=None, max_length=60)
    es_profesional: bool = False


class MunicipioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=2, max_length=120)
    departamento_id: int = Field(gt=0)


class PaginatedAdmin[T](BaseModel):
    data: list[T]
    total: int
    page: int
    per_page: int
    pages: int
