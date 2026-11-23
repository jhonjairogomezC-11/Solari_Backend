"""Login/registro con Google mediante OpenID Connect.

Seguridad:
- El id_token se verifica del lado backend con la librería oficial de Google
  (`google-auth`), que valida firma, emisor (`accounts.google.com`), audiencia
  (client_id) y expiración. No se confía en ningún dato enviado por el cliente.
- Si el correo de Google no está verificado, se rechaza.
- No se vincula automáticamente una cuenta de Google a una cuenta LOCAL existente
  solo porque coincida el email (se exigiría un flujo de vinculación explícito).
- El rol de una cuenta NUEVA lo decide el usuario (voluntario/fundación); nunca lo
  determina Google. Las cuentas existentes conservan su rol del backend.

Requiere configurar GOOGLE_CLIENT_ID (y opcionalmente GOOGLE_ALLOWED_AUDIENCES)
en el entorno. Sin esa configuración, el endpoint responde 503.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError, AuthError, ConflictError
from app.models.usuario import (
    ESTADO_ACTIVO,
    PROVIDER_GOOGLE,
    PROVIDER_LOCAL,
    Usuario,
)
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.auth import TokenResponse
from app.services.auth_service import AuthService

logger = logging.getLogger("solari.google")

_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleAuthService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings
        self.repo = UsuarioRepository(db)
        self.auth = AuthService(db, settings)

    def _verificar_id_token(self, id_token_str: str) -> dict[str, Any]:
        """Verificación síncrona del id_token (se ejecuta en threadpool)."""
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        audiences = self.settings.google_audiences_list
        request = google_requests.Request()

        # verify_oauth2_token valida firma, exp e iss; comprobamos audiencia manual
        # para soportar múltiples client_id (web/android/ios).
        claims = google_id_token.verify_oauth2_token(id_token_str, request)

        if claims.get("iss") not in _GOOGLE_ISSUERS:
            raise AuthError("Emisor del token de Google no válido.")
        if audiences and claims.get("aud") not in audiences:
            raise AuthError("La audiencia del token de Google no está permitida.")
        return claims

    async def login_con_google(
        self,
        id_token_str: str,
        *,
        rol: str | None,
        ip: str | None,
        user_agent: str | None,
    ) -> TokenResponse:
        if not self.settings.google_audiences_list:
            raise AppError(
                "El inicio de sesión con Google no está configurado.", status_code=503
            )

        try:
            claims = await asyncio.to_thread(self._verificar_id_token, id_token_str)
        except AuthError:
            raise
        except Exception as exc:  # noqa: BLE001 - token inválido / error de verificación
            logger.info("Fallo verificando id_token de Google: %s", type(exc).__name__)
            raise AuthError("Token de Google inválido.") from exc

        email = claims.get("email")
        email_verificado = bool(claims.get("email_verified", False))
        provider_id = claims.get("sub")
        nombre = claims.get("name") or (email.split("@")[0] if email else "Usuario")

        if not email or not provider_id:
            raise AuthError("El token de Google no contiene los datos requeridos.")
        if not email_verificado:
            raise AuthError("El correo de la cuenta de Google no está verificado.")

        # 1) ¿Existe ya una cuenta GOOGLE con este sub? -> login directo.
        usuario = await self.repo.por_provider_id(PROVIDER_GOOGLE, provider_id)

        if usuario is None:
            # 2) ¿Hay una cuenta LOCAL con el mismo email? No vincular automáticamente.
            local = await self.repo.por_email_local(email)
            if local is not None:
                raise ConflictError(
                    "Ya existe una cuenta local con este correo. Inicia sesión con tu "
                    "contraseña y vincula Google desde tu perfil."
                )

            # 3) Cuenta nueva: el rol lo define el usuario.
            if rol is None:
                raise ConflictError(
                    "Selecciona el tipo de cuenta (VOLUNTARIO o FUNDACION) para continuar."
                )
            usuario = Usuario(
                nombre=nombre,
                email=email,
                password_hash=None,
                provider=PROVIDER_GOOGLE,
                provider_id=provider_id,
                rol=rol,
                estado=ESTADO_ACTIVO,
                email_verificado=True,
            )
            self.repo.add(usuario)
            await self.db.flush()
            # Nota: el perfil (voluntario/fundación) se completa en un paso posterior
            # del onboarding, igual que ocurre con el backend actual.

        if usuario.estado != ESTADO_ACTIVO:
            raise AuthError("Tu cuenta no está activa.")

        access, expires_in = _crear_access(self.auth, usuario)
        refresh = await self.auth.tokens.emitir_refresh_token(
            usuario.id, ip=ip, user_agent=user_agent
        )
        await self.db.commit()

        from app.schemas.auth import UsuarioOut

        return TokenResponse(
            usuario=UsuarioOut.model_validate(usuario),
            token=access,
            refresh_token=refresh,
            expires_in=expires_in,
        )


def _crear_access(auth: AuthService, usuario: Usuario) -> tuple[str, int]:
    from app.core.security import create_access_token

    return create_access_token(
        auth.settings, subject=str(usuario.id), rol=usuario.rol, estado=usuario.estado
    )


# Nota: PROVIDER_LOCAL se importa para documentar la distinción de proveedores.
_ = PROVIDER_LOCAL
