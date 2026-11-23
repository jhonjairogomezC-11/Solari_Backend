"""Reglas de negocio del centro de soporte: tickets y solicitudes de cuenta."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.soporte import ESTADO_CERRADO, ESTADO_EN_REVISION, TicketSoporte
from app.repositories.soporte_repo import SoporteRepository


def _now() -> datetime:
    return datetime.now(UTC)


class SoporteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SoporteRepository(db)

    # ── Tickets ──
    async def crear_ticket(
        self,
        usuario_id: uuid.UUID,
        categoria: str,
        asunto: str,
        descripcion: str,
        adjunto_url: str | None,
    ) -> TicketSoporte:
        ticket = self.repo.crear_ticket(
            usuario_id, categoria, asunto, descripcion, adjunto_url
        )
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def mis_tickets(self, usuario_id: uuid.UUID) -> list[TicketSoporte]:
        return await self.repo.mis_tickets(usuario_id)

    async def detalle(self, ticket_id: uuid.UUID, usuario_id: uuid.UUID) -> dict:
        ticket = await self.repo.ticket_por_id(ticket_id)
        if ticket is None or ticket.usuario_id != usuario_id:
            raise NotFoundError("Ticket no encontrado.")
        mensajes = await self.repo.mensajes_de(ticket_id)
        return {"ticket": ticket, "mensajes": mensajes}

    async def responder_ticket(
        self, ticket_id: uuid.UUID, usuario_id: uuid.UUID, mensaje: str, adjunto_url: str | None
    ) -> TicketSoporte:
        ticket = await self.repo.ticket_por_id(ticket_id)
        if ticket is None or ticket.usuario_id != usuario_id:
            raise NotFoundError("Ticket no encontrado.")
        if ticket.estado == ESTADO_CERRADO:
            raise ConflictError("Este ticket está cerrado. Abre uno nuevo si lo necesitas.")

        self.repo.crear_mensaje(ticket_id, usuario_id, False, mensaje, adjunto_url)
        # Si el voluntario aporta información, el ticket vuelve a revisión.
        ticket.estado = ESTADO_EN_REVISION
        ticket.fecha_actualizacion = _now()
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def cerrar_ticket(
        self, ticket_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> TicketSoporte:
        ticket = await self.repo.ticket_por_id(ticket_id)
        if ticket is None or ticket.usuario_id != usuario_id:
            raise NotFoundError("Ticket no encontrado.")
        ticket.estado = ESTADO_CERRADO
        ticket.fecha_actualizacion = _now()
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    # ── Solicitudes de cuenta/privacidad ──
    async def crear_solicitud(
        self, usuario_id: uuid.UUID, tipo: str, motivo: str | None
    ):
        # Control de seguridad: una solicitud del mismo tipo no puede duplicarse
        # mientras esté pendiente/en proceso. Las de alto impacto NO se ejecutan
        # automáticamente: quedan PENDIENTE para revisión administrativa.
        existente = await self.repo.solicitud_pendiente(usuario_id, tipo)
        if existente is not None:
            raise ConflictError(
                "Ya tienes una solicitud de este tipo en curso. Espera su resolución."
            )
        solicitud = self.repo.crear_solicitud(usuario_id, tipo, motivo)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(solicitud)
        return solicitud

    async def mis_solicitudes(self, usuario_id: uuid.UUID):
        return await self.repo.mis_solicitudes(usuario_id)
