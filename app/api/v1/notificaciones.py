"""Endpoints de notificaciones (cualquier usuario autenticado)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbDep
from app.core.exceptions import NotFoundError
from app.schemas.notificacion import NotificacionOut
from app.services.notificacion_service import NotificacionService

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


@router.get("")
async def listar(
    db: DbDep,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    filas, total = await NotificacionService(db).listar(user.id, page, per_page)
    return {
        "data": [NotificacionOut.model_validate(f) for f in filas],
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
