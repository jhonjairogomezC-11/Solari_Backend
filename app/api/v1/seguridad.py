"""Endpoints de seguridad de cuenta: sesiones activas y verificación en dos pasos.

La sesión actual se identifica con la cabecera opcional `X-Refresh-Token` (el refresh
token que ya guarda el cliente). Solo se compara su hash; nunca se registra ni se
devuelve. Sin la cabecera, el listado funciona pero ninguna sesión queda marcada.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Request

from app.api.deps import CurrentUser, DbDep, SettingsDep
from app.core.rate_limit import limiter
from app.schemas.auth import MessageResponse
from app.schemas.seguridad import (
    MfaCodigoInput,
    MfaConfirmarOut,
    MfaDesactivarInput,
    MfaEstadoOut,
    MfaIniciarOut,
    SesionesRevocadasOut,
    SesionOut,
)
from app.services.seguridad_service import MfaService, SesionesService

router = APIRouter(prefix="/cuenta", tags=["seguridad"])

RefreshHeader = Annotated[str | None, Header(alias="X-Refresh-Token", max_length=512)]


# ─────────────────────────── Sesiones activas ───────────────────────────


@router.get("/sesiones", response_model=list[SesionOut])
async def listar_sesiones(
    db: DbDep, user: CurrentUser, x_refresh_token: RefreshHeader = None
) -> list[SesionOut]:
    return await SesionesService(db).listar(user.id, x_refresh_token)


@router.post("/sesiones/cerrar-otras", response_model=SesionesRevocadasOut)
@limiter.limit("10/minute")
async def cerrar_otras_sesiones(
    request: Request, db: DbDep, user: CurrentUser, x_refresh_token: RefreshHeader = None
) -> SesionesRevocadasOut:
    n = await SesionesService(db).cerrar_otras(user.id, x_refresh_token)
    return SesionesRevocadasOut(message="Se cerraron las demás sesiones.", revocadas=n)


@router.delete("/sesiones/{sesion_id}", response_model=MessageResponse)
async def revocar_sesion(sesion_id: uuid.UUID, db: DbDep, user: CurrentUser) -> MessageResponse:
    await SesionesService(db).revocar(user.id, sesion_id)
    return MessageResponse(message="Sesión cerrada.")


# ─────────────────────────── Verificación en dos pasos ───────────────────────────


@router.get("/mfa", response_model=MfaEstadoOut)
async def estado_mfa(db: DbDep, settings: SettingsDep, user: CurrentUser) -> MfaEstadoOut:
    return MfaService(db, settings).estado(user)


@router.post("/mfa/iniciar", response_model=MfaIniciarOut)
@limiter.limit("10/minute")
async def iniciar_mfa(
    request: Request, db: DbDep, settings: SettingsDep, user: CurrentUser
) -> MfaIniciarOut:
    return await MfaService(db, settings).iniciar(user)


@router.post("/mfa/confirmar", response_model=MfaConfirmarOut)
@limiter.limit("5/minute")
async def confirmar_mfa(
    request: Request,
    data: MfaCodigoInput,
    db: DbDep,
    settings: SettingsDep,
    user: CurrentUser,
) -> MfaConfirmarOut:
    return await MfaService(db, settings).confirmar(user, data.codigo)


@router.post("/mfa/desactivar", response_model=MessageResponse)
@limiter.limit("5/minute")
async def desactivar_mfa(
    request: Request,
    data: MfaDesactivarInput,
    db: DbDep,
    settings: SettingsDep,
    user: CurrentUser,
) -> MessageResponse:
    await MfaService(db, settings).desactivar(user, data.password, data.codigo)
    return MessageResponse(message="Verificación en dos pasos desactivada.")
