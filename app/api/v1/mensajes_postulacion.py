"""Endpoints de mensajería dentro de una postulación (voluntario ↔ organización)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, DbDep
from app.core.rate_limit import limiter
from app.schemas.mensaje_postulacion import (
    ConversacionPostulacionOut,
    MensajePostulacionInput,
    NoLeidosOut,
)
from app.services.mensaje_postulacion_service import MensajePostulacionService

router = APIRouter(tags=["mensajes"])


@router.get(
    "/postulaciones/{postulacion_id}/mensajes", response_model=ConversacionPostulacionOut
)
async def listar_mensajes(db: DbDep, user: CurrentUser, postulacion_id: uuid.UUID):
    """Historial de la conversación. Marca como leídos los mensajes de la otra parte."""
    return await MensajePostulacionService(db).listar(user, postulacion_id)


@router.post(
    "/postulaciones/{postulacion_id}/mensajes",
    response_model=ConversacionPostulacionOut,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def enviar_mensaje(
    request: Request,
    db: DbDep,
    user: CurrentUser,
    postulacion_id: uuid.UUID,
    data: MensajePostulacionInput,
):
    return await MensajePostulacionService(db).enviar(user, postulacion_id, data)


@router.get("/mensajes/no-leidos", response_model=NoLeidosOut)
async def mensajes_no_leidos(db: DbDep, user: CurrentUser):
    return NoLeidosOut(total=await MensajePostulacionService(db).no_leidos(user))
