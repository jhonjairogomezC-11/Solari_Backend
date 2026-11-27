"""Router del panel de administración. Todos los endpoints exigen rol ADMIN."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbDep, require_roles
from app.models.usuario import ROL_ADMIN
from app.schemas.admin import (
    AdminConvocatoriaOut,
    AdminFundacionOut,
    AdminPostulacionOut,
    AdminUsuarioOut,
    AdminVoluntarioOut,
    CambiarEstadoUsuario,
    CambiarRolUsuario,
    CatalogoItemCreate,
    DashboardStats,
    HabilidadCreate,
    MunicipioCreate,
    OcultarConvocatoria,
    PaginatedAdmin,
    VerificarFundacion,
    VerificarVoluntario,
    RechazarDocumentoVoluntario,
)
from app.schemas.catalogo import (
    AreaImpactoOut,
    DepartamentoOut,
    HabilidadOut,
    MunicipioOut,
)
from app.services.admin_service import AdminService

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles(ROL_ADMIN))],
)

PageQ = Annotated[int, Query(ge=1)]
PerPageQ = Annotated[int, Query(ge=1, le=100)]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(db: DbDep, _: CurrentUser):
    return await AdminService(db).dashboard()


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------
@router.get("/usuarios", response_model=PaginatedAdmin[AdminUsuarioOut])
async def listar_usuarios(
    db: DbDep,
    _: CurrentUser,
    page: PageQ = 1,
    per_page: PerPageQ = 20,
    rol: str | None = None,
    estado: str | None = None,
    buscar: str | None = None,
):
    return await AdminService(db).listar_usuarios(page, per_page, rol, estado, buscar)


@router.patch("/usuarios/{usuario_id}/estado", response_model=AdminUsuarioOut)
async def cambiar_estado_usuario(
    usuario_id: str, body: CambiarEstadoUsuario, db: DbDep, admin: CurrentUser
):
    return await AdminService(db).cambiar_estado_usuario(
        admin.id, usuario_id, body.estado, body.motivo
    )


@router.patch("/usuarios/{usuario_id}/rol", response_model=AdminUsuarioOut)
async def cambiar_rol_usuario(
    usuario_id: str, body: CambiarRolUsuario, db: DbDep, admin: CurrentUser
):
    return await AdminService(db).cambiar_rol_usuario(admin.id, usuario_id, body.rol)


# ---------------------------------------------------------------------------
# Fundaciones (verificación)
# ---------------------------------------------------------------------------
@router.get("/fundaciones", response_model=PaginatedAdmin[AdminFundacionOut])
async def listar_fundaciones(
    db: DbDep,
    _: CurrentUser,
    page: PageQ = 1,
    per_page: PerPageQ = 20,
    estado_verificacion: str | None = None,
    buscar: str | None = None,
):
    return await AdminService(db).listar_fundaciones(
        page, per_page, estado_verificacion, buscar
    )


@router.get("/fundaciones/{fundacion_id}", response_model=AdminFundacionOut)
async def obtener_fundacion(fundacion_id: str, db: DbDep, _: CurrentUser):
    return await AdminService(db).obtener_fundacion(fundacion_id)


@router.patch("/fundaciones/{fundacion_id}/verificacion", response_model=AdminFundacionOut)
async def verificar_fundacion(
    fundacion_id: str, body: VerificarFundacion, db: DbDep, admin: CurrentUser
):
    return await AdminService(db).verificar_fundacion(
        admin.id, fundacion_id, body.estado, body.motivo
    )


# ---------------------------------------------------------------------------
# Convocatorias (moderación)
# ---------------------------------------------------------------------------
@router.get("/convocatorias", response_model=PaginatedAdmin[AdminConvocatoriaOut])
async def listar_convocatorias(
    db: DbDep,
    _: CurrentUser,
    page: PageQ = 1,
    per_page: PerPageQ = 20,
    estado: str | None = None,
    oculta: bool | None = None,
    buscar: str | None = None,
):
    return await AdminService(db).listar_convocatorias(page, per_page, estado, oculta, buscar)


@router.patch("/convocatorias/{publicacion_id}/moderacion", response_model=AdminConvocatoriaOut)
async def moderar_convocatoria(
    publicacion_id: str, body: OcultarConvocatoria, db: DbDep, admin: CurrentUser
):
    return await AdminService(db).ocultar_convocatoria(
        admin.id, publicacion_id, body.ocultar, body.motivo
    )


# ---------------------------------------------------------------------------
# Voluntarios (verificación de identidad)
# ---------------------------------------------------------------------------
@router.get("/voluntarios", response_model=PaginatedAdmin[AdminVoluntarioOut])
async def listar_voluntarios(
    db: DbDep,
    _: CurrentUser,
    page: PageQ = 1,
    per_page: PerPageQ = 20,
    verificado: bool | None = None,
    con_documento: bool | None = None,
    buscar: str | None = None,
):
    return await AdminService(db).listar_voluntarios(
        page, per_page, verificado, con_documento, buscar
    )


@router.patch("/voluntarios/{voluntario_id}/verificacion", response_model=AdminVoluntarioOut)
async def verificar_voluntario(
    voluntario_id: str, body: VerificarVoluntario, db: DbDep, admin: CurrentUser
):
    return await AdminService(db).verificar_voluntario(admin.id, voluntario_id, body.verificado)


@router.post("/voluntarios/{voluntario_id}/rechazar-documento", response_model=AdminVoluntarioOut)
async def rechazar_documento_voluntario(
    voluntario_id: str, body: RechazarDocumentoVoluntario, db: DbDep, admin: CurrentUser
):
    return await AdminService(db).rechazar_documento_voluntario(admin.id, voluntario_id, body.motivo)


# ---------------------------------------------------------------------------
# Postulaciones (vista global)
# ---------------------------------------------------------------------------
@router.get("/postulaciones", response_model=PaginatedAdmin[AdminPostulacionOut])
async def listar_postulaciones(
    db: DbDep,
    _: CurrentUser,
    page: PageQ = 1,
    per_page: PerPageQ = 20,
    estado: str | None = None,
):
    return await AdminService(db).listar_postulaciones(page, per_page, estado)


# ---------------------------------------------------------------------------
# Catálogos (CRUD aditivo)
# ---------------------------------------------------------------------------
@router.post("/catalogos/areas-impacto", response_model=AreaImpactoOut, status_code=201)
async def crear_area(body: CatalogoItemCreate, db: DbDep, admin: CurrentUser):
    return await AdminService(db).crear_area(admin.id, body.nombre)


@router.post("/catalogos/habilidades", response_model=HabilidadOut, status_code=201)
async def crear_habilidad(body: HabilidadCreate, db: DbDep, admin: CurrentUser):
    return await AdminService(db).crear_habilidad(
        admin.id, body.nombre, body.categoria, body.es_profesional
    )


@router.post("/catalogos/departamentos", response_model=DepartamentoOut, status_code=201)
async def crear_departamento(body: CatalogoItemCreate, db: DbDep, admin: CurrentUser):
    return await AdminService(db).crear_departamento(admin.id, body.nombre)


@router.post("/catalogos/municipios", response_model=MunicipioOut, status_code=201)
async def crear_municipio(body: MunicipioCreate, db: DbDep, admin: CurrentUser):
    return await AdminService(db).crear_municipio(admin.id, body.nombre, body.departamento_id)
