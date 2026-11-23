"""Acceso a datos del centro de soporte."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.soporte import (
    SolicitudCuenta,
    TicketMensaje,
    TicketSoporte,
)


class SoporteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Tickets ──
    def crear_ticket(
        self,
        usuario_id: uuid.UUID,
        categoria: str,
        asunto: str,
        descripcion: str,
        adjunto_url: str | None,
    ) -> TicketSoporte:
        ticket = TicketSoporte(
            usuario_id=usuario_id,
            categoria=categoria,
            asunto=asunto,
            descripcion=descripcion,
            adjunto_url=adjunto_url,
        )
        self.db.add(ticket)
        return ticket

    async def ticket_por_id(self, ticket_id: uuid.UUID) -> TicketSoporte | None:
        return await self.db.get(TicketSoporte, ticket_id)

    async def mis_tickets(self, usuario_id: uuid.UUID) -> list[TicketSoporte]:
        stmt = (
            select(TicketSoporte)
            .where(TicketSoporte.usuario_id == usuario_id)
            .order_by(TicketSoporte.fecha_creacion.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def mensajes_de(self, ticket_id: uuid.UUID) -> list[TicketMensaje]:
        stmt = (
            select(TicketMensaje)
            .where(TicketMensaje.ticket_id == ticket_id)
            .order_by(TicketMensaje.fecha_creacion)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    def crear_mensaje(
        self,
        ticket_id: uuid.UUID,
        autor_id: uuid.UUID,
        es_admin: bool,
        mensaje: str,
        adjunto_url: str | None,
    ) -> TicketMensaje:
        m = TicketMensaje(
            ticket_id=ticket_id,
            autor_id=autor_id,
            es_admin=es_admin,
            mensaje=mensaje,
            adjunto_url=adjunto_url,
        )
        self.db.add(m)
        return m

    # ── Solicitudes de cuenta ──
    def crear_solicitud(
        self, usuario_id: uuid.UUID, tipo: str, motivo: str | None
    ) -> SolicitudCuenta:
        s = SolicitudCuenta(usuario_id=usuario_id, tipo=tipo, motivo=motivo)
        self.db.add(s)
        return s

    async def solicitud_pendiente(
        self, usuario_id: uuid.UUID, tipo: str
    ) -> SolicitudCuenta | None:
        from app.models.soporte import SOL_ESTADO_EN_PROCESO, SOL_ESTADO_PENDIENTE

        stmt = select(SolicitudCuenta).where(
            SolicitudCuenta.usuario_id == usuario_id,
            SolicitudCuenta.tipo == tipo,
            SolicitudCuenta.estado.in_([SOL_ESTADO_PENDIENTE, SOL_ESTADO_EN_PROCESO]),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def mis_solicitudes(self, usuario_id: uuid.UUID) -> list[SolicitudCuenta]:
        stmt = (
            select(SolicitudCuenta)
            .where(SolicitudCuenta.usuario_id == usuario_id)
            .order_by(SolicitudCuenta.fecha_creacion.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())
