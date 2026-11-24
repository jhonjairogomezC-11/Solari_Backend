"""Endpoints de autenticación (/api/v1/auth).

Compatibilidad móvil: se conservan las rutas y el formato de respuesta que la app
Flutter ya consume. Además se exponen endpoints explícitos por tipo de cuenta.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Path, Request, status
from pydantic import ValidationError

from app.api.deps import (
    CurrentUser,
    DbDep,
    SettingsDep,
    client_ip,
    user_agent,
)
from app.core.exceptions import HTTP_422, AppError
from app.core.rate_limit import limiter
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterFundacionRequest,
    RegisterVoluntarioRequest,
    ResetPasswordRequest,
    TokenResponse,
    UsuarioOut,
)
from app.schemas.seguridad import LoginMfaRequest, MfaRequeridoResponse
from app.services.auth_service import AuthService
from app.services.google_service import GoogleAuthService

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = None  # placeholder para rate-limit strings (se leen de settings vía closure)


def _ip(request: Request) -> str | None:
    return client_ip(request)


def _ua(request: Request) -> str | None:
    return user_agent(request)


# ─────────────────────────── Registro ───────────────────────────


@router.post(
    "/register/volunteer",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/hour")
async def register_volunteer(
    request: Request,
    data: RegisterVoluntarioRequest,
    db: DbDep,
    settings: SettingsDep,
) -> TokenResponse:
    service = AuthService(db, settings)
    return await service.registrar_voluntario(data, ip=_ip(request), user_agent=_ua(request))


@router.post(
    "/register/foundation",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/hour")
async def register_foundation(
    request: Request,
    data: RegisterFundacionRequest,
    db: DbDep,
    settings: SettingsDep,
) -> TokenResponse:
    service = AuthService(db, settings)
    return await service.registrar_fundacion(data, ip=_ip(request), user_agent=_ua(request))


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/hour")
async def register_legacy(
    request: Request,
    db: DbDep,
    settings: SettingsDep,
    payload: Annotated[dict[str, Any], Body(...)],
) -> TokenResponse:
    """Endpoint de compatibilidad con la app móvil actual.

    El móvil envía un único /auth/register con `rol` y los campos básicos. El
    `rol` se usa solo para enrutar al flujo correcto; nunca para conceder ADMIN.
    """
    rol = str(payload.get("rol", "")).upper()
    service = AuthService(db, settings)
    try:
        if rol == "VOLUNTARIO":
            data = RegisterVoluntarioRequest.model_validate(payload)
            return await service.registrar_voluntario(
                data, ip=_ip(request), user_agent=_ua(request)
            )
        if rol == "FUNDACION":
            data = RegisterFundacionRequest.model_validate(payload)
            return await service.registrar_fundacion(
                data, ip=_ip(request), user_agent=_ua(request)
            )
    except ValidationError:
        # Reusa el manejador global devolviendo 422 con el mismo formato.
        raise
    raise AppError(
        "El campo 'rol' debe ser VOLUNTARIO o FUNDACION.",
        HTTP_422,
    )


# ─────────────────────────── Login / sesión ───────────────────────────


@router.post("/login", response_model=TokenResponse | MfaRequeridoResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    data: LoginRequest,
    db: DbDep,
    settings: SettingsDep,
) -> TokenResponse | MfaRequeridoResponse:
    """Sin MFA: respuesta de tokens habitual. Con MFA: {mfa_requerido, mfa_token}."""
    service = AuthService(db, settings)
    return await service.login(
        data.email, data.password, ip=_ip(request), user_agent=_ua(request)
    )


@router.post("/login/mfa", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login_mfa(
    request: Request,
    data: LoginMfaRequest,
    db: DbDep,
    settings: SettingsDep,
) -> TokenResponse:
    """Segundo paso: código TOTP (6 dígitos) o código de respaldo de un solo uso."""
    service = AuthService(db, settings)
    return await service.login_mfa(
        data.mfa_token, data.codigo, ip=_ip(request), user_agent=_ua(request)
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    data: RefreshRequest,
    db: DbDep,
    settings: SettingsDep,
) -> TokenResponse:
    service = AuthService(db, settings)
    return await service.refresh(
        data.refresh_token, ip=_ip(request), user_agent=_ua(request)
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(user: CurrentUser, db: DbDep, settings: SettingsDep) -> MessageResponse:
    service = AuthService(db, settings)
    await service.logout(user.id)
    return MessageResponse(message="Sesión cerrada correctamente.")


@router.post("/revoke-refresh", response_model=dict)
async def revoke_refresh(user: CurrentUser, db: DbDep, settings: SettingsDep) -> dict:
    service = AuthService(db, settings)
    count = await service.revocar_refresh(user.id)
    return {"message": "Refresh tokens revocados.", "revocados": count}


@router.get("/me", response_model=UsuarioOut)
async def me(user: CurrentUser) -> UsuarioOut:
    return UsuarioOut.model_validate(user)


# ─────────────────────────── Verificación de email ───────────────────────────


@router.get("/verify-email/{token}", response_model=MessageResponse)
async def verify_email(
    db: DbDep,
    settings: SettingsDep,
    token: Annotated[str, Path(min_length=1)],
) -> MessageResponse:
    service = AuthService(db, settings)
    ok = await service.verificar_email(token)
    if not ok:
        raise AppError("Token inválido o expirado.", status.HTTP_400_BAD_REQUEST)
    return MessageResponse(message="Email verificado correctamente.")


# ─────────────────────────── Recuperación de contraseña ───────────────────────────


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/hour")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: DbDep,
    settings: SettingsDep,
) -> MessageResponse:
    service = AuthService(db, settings)
    await service.solicitar_reset(data.email, ip=_ip(request), user_agent=_ua(request))
    # Respuesta genérica siempre, exista o no el email.
    return MessageResponse(message="Si el email existe, recibirás un enlace de recuperación.")


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/hour")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: DbDep,
    settings: SettingsDep,
) -> MessageResponse:
    if not data.passwords_coinciden():
        raise AppError("Las contraseñas no coinciden.", HTTP_422)
    service = AuthService(db, settings)
    ok = await service.reset_password(data.token, data.password)
    if not ok:
        raise AppError("Token inválido o expirado.", status.HTTP_400_BAD_REQUEST)
    return MessageResponse(message="Contraseña actualizada correctamente.")


# ─────────────────────────── Google OIDC ───────────────────────────


@router.post("/google", response_model=TokenResponse | MfaRequeridoResponse)
@limiter.limit("10/minute")
async def google_login(
    request: Request,
    data: GoogleLoginRequest,
    db: DbDep,
    settings: SettingsDep,
) -> TokenResponse | MfaRequeridoResponse:
    service = GoogleAuthService(db, settings)
    return await service.login_con_google(
        data.id_token, rol=data.rol, ip=_ip(request), user_agent=_ua(request)
    )
