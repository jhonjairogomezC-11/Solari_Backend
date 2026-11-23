"""Endpoints del centro de soporte (cualquier usuario autenticado)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbDep
from app.schemas.soporte import (
    SolicitudCuentaCreate,
    SolicitudCuentaOut,
    TicketCreate,
    TicketDetalleOut,
    TicketMensajeInput,
    TicketMensajeOut,
    TicketOut,
)
from app.services.soporte_service import SoporteService

router = APIRouter(prefix="/soporte", tags=["soporte"])


# ─────────────── Tickets ───────────────

@router.post("/tickets", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def crear_ticket(db: DbDep, user: CurrentUser, data: TicketCreate):
    return await SoporteService(db).crear_ticket(
        user.id, data.categoria, data.asunto, data.descripcion, data.adjunto_url
    )


@router.get("/tickets", response_model=list[TicketOut])
async def mis_tickets(db: DbDep, user: CurrentUser):
    return await SoporteService(db).mis_tickets(user.id)


@router.get("/tickets/{ticket_id}", response_model=TicketDetalleOut)
async def detalle_ticket(db: DbDep, user: CurrentUser, ticket_id: uuid.UUID):
    res = await SoporteService(db).detalle(ticket_id, user.id)
    ticket = res["ticket"]
    return TicketDetalleOut(
        **TicketOut.model_validate(ticket).model_dump(),
        mensajes=[TicketMensajeOut.model_validate(m) for m in res["mensajes"]],
    )


@router.post("/tickets/{ticket_id}/responder", response_model=TicketOut)
async def responder_ticket(
    db: DbDep, user: CurrentUser, ticket_id: uuid.UUID, data: TicketMensajeInput
):
    return await SoporteService(db).responder_ticket(
        ticket_id, user.id, data.mensaje, data.adjunto_url
    )


@router.post("/tickets/{ticket_id}/cerrar", response_model=TicketOut)
async def cerrar_ticket(db: DbDep, user: CurrentUser, ticket_id: uuid.UUID):
    return await SoporteService(db).cerrar_ticket(ticket_id, user.id)


# ─────────────── Solicitudes de cuenta / privacidad ───────────────

@router.post(
    "/solicitudes-cuenta",
    response_model=SolicitudCuentaOut,
    status_code=status.HTTP_201_CREATED,
)
async def crear_solicitud(db: DbDep, user: CurrentUser, data: SolicitudCuentaCreate):
    return await SoporteService(db).crear_solicitud(user.id, data.tipo, data.motivo)


@router.get("/solicitudes-cuenta", response_model=list[SolicitudCuentaOut])
async def mis_solicitudes(db: DbDep, user: CurrentUser):
    return await SoporteService(db).mis_solicitudes(user.id)
