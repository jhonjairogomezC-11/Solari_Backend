"""Panel de administración: soporte, privacidad, verificación, reseñas y auditoría.

Todos los endpoints exigen rol ADMIN.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbDep, require_roles
from app.models.usuario import ROL_ADMIN
from app.schemas.admin import PaginatedAdmin
from app.schemas.admin_gestion import (
    AdminModerarResena,
    AdminResenaOut,
    AdminResolverSolicitud,
    AdminResolverVerificacion,
    AdminResponderTicket,
    AdminSolicitudOut,
    AdminTicketDetalle,
    AdminTicketOut,
    AdminVerificacionOut,
    AuditoriaOut,
)
from app.services.admin_gestion_service import AdminGestionService

router = APIRouter(
    prefix="/admin",
    tags=["admin-gestion"],
    dependencies=[Depends(require_roles(ROL_ADMIN))],
)

PageQ = Annotated[int, Query(ge=1)]
PerPageQ = Annotated[int, Query(ge=1, le=100)]


# ─────────────── Soporte ───────────────

@router.get("/soporte/tickets", response_model=PaginatedAdmin[AdminTicketOut])
async def listar_tickets(
    db: DbDep, _: CurrentUser, page: PageQ = 1, per_page: PerPageQ = 20,
    estado: str | None = None, categoria: str | None = None,
    buscar: str | None = Query(default=None, max_length=120),
):
    return await AdminGestionService(db).listar_tickets(page, per_page, estado, categoria, buscar)


@router.get("/soporte/tickets/{ticket_id}", response_model=AdminTicketDetalle)
async def detalle_ticket(db: DbDep, _: CurrentUser, ticket_id: uuid.UUID):
    return await AdminGestionService(db).detalle_ticket(ticket_id)


@router.post("/soporte/tickets/{ticket_id}/responder", response_model=AdminTicketDetalle)
async def responder_ticket(
    db: DbDep, admin: CurrentUser, ticket_id: uuid.UUID, data: AdminResponderTicket
):
    return await AdminGestionService(db).responder_ticket(
        admin, ticket_id, data.mensaje, data.estado
    )


# ─────────────── Solicitudes de cuenta / privacidad ───────────────

@router.get("/solicitudes-cuenta", response_model=PaginatedAdmin[AdminSolicitudOut])
async def listar_solicitudes(
    db: DbDep, _: CurrentUser, page: PageQ = 1, per_page: PerPageQ = 20,
    estado: str | None = None, tipo: str | None = None,
):
    return await AdminGestionService(db).listar_solicitudes(page, per_page, estado, tipo)


@router.put("/solicitudes-cuenta/{solicitud_id}", response_model=AdminSolicitudOut)
async def resolver_solicitud(
    db: DbDep, admin: CurrentUser, solicitud_id: uuid.UUID, data: AdminResolverSolicitud
):
    return await AdminGestionService(db).resolver_solicitud(admin, solicitud_id, data)


# ─────────────── Verificación documental ───────────────

@router.get("/verificaciones", response_model=PaginatedAdmin[AdminVerificacionOut])
async def listar_verificaciones(
    db: DbDep, _: CurrentUser, page: PageQ = 1, per_page: PerPageQ = 20,
    estado: str | None = None,
):
    return await AdminGestionService(db).listar_verificaciones(page, per_page, estado)


@router.put("/verificaciones/{fundacion_id}", response_model=AdminVerificacionOut)
async def resolver_verificacion(
    db: DbDep, admin: CurrentUser, fundacion_id: uuid.UUID, data: AdminResolverVerificacion
):
    return await AdminGestionService(db).resolver_verificacion(
        admin, fundacion_id, data.accion, data.nota
    )


# ─────────────── Reseñas ───────────────

@router.get("/resenas", response_model=PaginatedAdmin[AdminResenaOut])
async def listar_resenas(
    db: DbDep, _: CurrentUser, page: PageQ = 1, per_page: PerPageQ = 20,
    estado: str | None = None,
):
    return await AdminGestionService(db).listar_resenas(page, per_page, estado)


@router.put("/resenas/{resena_id}", status_code=204)
async def moderar_resena(
    db: DbDep, admin: CurrentUser, resena_id: uuid.UUID, data: AdminModerarResena
):
    await AdminGestionService(db).moderar_resena(admin, resena_id, data.accion, data.motivo)


# ─────────────── Auditoría ───────────────

@router.get("/auditoria", response_model=PaginatedAdmin[AuditoriaOut])
async def auditoria(
    db: DbDep, _: CurrentUser, page: PageQ = 1, per_page: PerPageQ = 20,
    tipo: str | None = None,
):
    return await AdminGestionService(db).listar_auditoria(page, per_page, tipo)
