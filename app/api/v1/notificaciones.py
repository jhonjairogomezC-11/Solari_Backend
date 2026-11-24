"""Endpoints de notificaciones (cualquier usuario autenticado)."""

from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep, SettingsDep
from app.core.exceptions import AuthError, NotFoundError
from app.core.rate_limit import limiter
from app.core.security import create_sse_ticket, decode_sse_ticket
from app.models.postulacion import Postulacion
from app.models.usuario import ESTADO_ACTIVO
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.notificacion import NotificacionOut
from app.services.notificacion_service import NotificacionService
from app.services.notificacion_stream import eventos_notificaciones

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


@router.post("/stream-ticket")
@limiter.limit("30/minute")
async def stream_ticket(request: Request, user: CurrentUser, settings: SettingsDep):
    """Ticket de 60 s para abrir el stream SSE (EventSource no envía Authorization)."""
    ticket, expira = create_sse_ticket(settings, subject=str(user.id))
    return {"ticket": ticket, "expires_in": expira}


@router.get("/stream")
async def stream(
    request: Request,
    db: DbDep,
    settings: SettingsDep,
    ticket: str = Query(..., min_length=10, max_length=2048),
):
    """Stream SSE: emite `event: notificacion` con {no_leidas, ultima?} al cambiar el conteo."""
    try:
        payload = decode_sse_ticket(settings, ticket)
        usuario_id = uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, ValueError) as exc:
        raise AuthError("Ticket inválido o vencido.") from exc
    usuario = await UsuarioRepository(db).por_id(usuario_id)
    if usuario is None or usuario.estado != ESTADO_ACTIVO:
        raise AuthError("Ticket inválido o vencido.")
    # La sesión de la petición no se usa dentro del stream: el generador abre
    # sesiones cortas propias para no retener una conexión del pool.
    await db.close()
    return StreamingResponse(
        eventos_notificaciones(usuario_id, request.is_disconnected),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("")
async def listar(
    db: DbDep,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    filas, total = await NotificacionService(db).listar(user.id, page, per_page)
    post_ids = {f.objeto_id for f in filas if f.objeto_tipo == "postulacion" and f.objeto_id}
    pub_por_post: dict[uuid.UUID, uuid.UUID] = {}
    if post_ids:
        pub_por_post = {
            pid: pub
            for pid, pub in (
                await db.execute(
                    select(Postulacion.id, Postulacion.publicacion_id).where(
                        Postulacion.id.in_(post_ids)
                    )
                )
            ).all()
        }
    data = []
    for f in filas:
        out = NotificacionOut.model_validate(f)
        if f.objeto_tipo == "postulacion" and f.objeto_id:
            out.publicacion_id = pub_por_post.get(f.objeto_id)
        data.append(out)
    return {
        "data": data,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/no-leidas")
async def no_leidas(db: DbDep, user: CurrentUser):
    total = await NotificacionService(db).no_leidas(user.id)
    return {"total": total}


@router.post("/marcar-todas-leidas")
async def marcar_todas(db: DbDep, user: CurrentUser):
    n = await NotificacionService(db).marcar_todas_leidas(user.id)
    return {"message": f"{n} notificaciones marcadas como leídas.", "actualizadas": n}


@router.put("/{notificacion_id}/marcar-leida", response_model=NotificacionOut)
async def marcar_leida(db: DbDep, user: CurrentUser, notificacion_id: uuid.UUID):
    notif = await NotificacionService(db).marcar_leida(notificacion_id, user.id)
    if notif is None:
        raise NotFoundError("Notificación no encontrada.")
    return notif
