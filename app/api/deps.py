"""Dependencias compartidas de la API: settings, servicios y usuario autenticado."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthError, ForbiddenError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.usuario import ESTADO_ACTIVO, Usuario
from app.repositories.usuario_repo import UsuarioRepository

_bearer = HTTPBearer(auto_error=False)


def get_app_settings() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


async def get_current_user(
    db: DbDep,
    settings: SettingsDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Usuario:
    if creds is None or not creds.credentials:
        raise AuthError("No autenticado.")
    try:
        payload = decode_access_token(settings, creds.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("El token ha expirado.") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("Token inválido.") from exc

    sub = payload.get("sub")
    if not sub:
        raise AuthError("Token inválido.")

    repo = UsuarioRepository(db)
    usuario = await repo.por_id(sub)
    if usuario is None:
        raise AuthError("Token inválido.")
    if usuario.estado != ESTADO_ACTIVO:
        raise ForbiddenError("Tu cuenta no está activa.")
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def require_roles(*roles: str):
    """Fábrica de dependencias para exigir uno de los roles indicados."""

    async def _checker(user: CurrentUser) -> Usuario:
        if user.rol not in roles:
            raise ForbiddenError("No tienes permisos para esta acción.")
        return user

    return _checker
