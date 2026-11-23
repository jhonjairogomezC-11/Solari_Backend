"""Servicio de autenticación: registro, login, refresh, reset y verificación.

Principios de seguridad aplicados:
- Respuestas no enumerables: el registro con email duplicado y el login con
  credenciales inválidas devuelven mensajes genéricos equivalentes.
- Argon2id para nuevos hashes; verificación de bcrypt heredado con rehash perezoso.
- Rol/estado SIEMPRE fijados por el backend; nunca se leen del cliente.
- Tokens opacos hasheados; access JWT compatible con Laravel.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AuthError, ConflictError
from app.core.security import (
    create_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.fundacion import Fundacion
from app.models.usuario import (
    ESTADO_ACTIVO,
    ESTADO_BLOQUEADO,
    ESTADO_SUSPENDIDO,
    PROVIDER_LOCAL,
    ROL_FUNDACION,
    ROL_VOLUNTARIO,
    Usuario,
)
from app.models.voluntario import Voluntario
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.auth import (
    RegisterFundacionRequest,
    RegisterVoluntarioRequest,
    TokenResponse,
    UsuarioOut,
)
from app.services.legal_service import LegalService
from app.services.token_service import TokenService

logger = logging.getLogger("solari.auth")

# Mensaje genérico para no revelar si un email existe.
_GENERIC_INVALID_CREDS = "Correo o contraseña incorrectos."
_GENERIC_REGISTER_CONFLICT = (
    "No fue posible completar el registro con los datos proporcionados."
)


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings
        self.repo = UsuarioRepository(db)
        self.tokens = TokenService(db, settings)
        self.legal = LegalService(db)

    # ─────────────── Construcción de respuesta ───────────────

    async def _emitir_sesion(
        self, usuario: Usuario, *, ip: str | None, user_agent: str | None
    ) -> TokenResponse:
        access, expires_in = create_access_token(
            self.settings, subject=str(usuario.id), rol=usuario.rol, estado=usuario.estado
        )
        refresh = await self.tokens.emitir_refresh_token(
            usuario.id, ip=ip, user_agent=user_agent
        )
        return TokenResponse(
            usuario=UsuarioOut.model_validate(usuario),
            token=access,
            refresh_token=refresh,
            expires_in=expires_in,
        )

    # ─────────────── Registro ───────────────

    async def registrar_voluntario(
        self, data: RegisterVoluntarioRequest, *, ip: str | None, user_agent: str | None
    ) -> TokenResponse:
        if not data.passwords_coinciden():
            raise ConflictError("Las contraseñas no coinciden.")

        # No revela si el email ya existe: responde genérico de conflicto.
        if await self.repo.por_email_local(data.email):
            raise ConflictError(_GENERIC_REGISTER_CONFLICT)
        if await self.repo.existe_numero_documento(data.numero_documento):
            raise ConflictError(_GENERIC_REGISTER_CONFLICT)

        usuario = Usuario(
            nombre=data.nombre,
            email=data.email,
            password_hash=hash_password(data.password),
            provider=PROVIDER_LOCAL,
            telefono=data.telefono,
            rol=ROL_VOLUNTARIO,  # fijado por backend, nunca del cliente
            estado=ESTADO_ACTIVO,
            email_verificado=False,
        )
        self.repo.add(usuario)
        await self.db.flush()  # obtiene usuario.id

        perfil = Voluntario(
            usuario_id=usuario.id,
            tipo_documento=data.tipo_documento,
            numero_documento=data.numero_documento,
            fecha_nacimiento=data.fecha_nacimiento,
            genero=data.genero,
            municipio_id=data.municipio_id,
            disponibilidad=data.disponibilidad,
            experiencia=data.experiencia,
        )
        self.repo.add(perfil)

        await self.legal.registrar_aceptaciones(
            usuario_id=usuario.id,
            aceptaciones=data.aceptaciones,
            ip=ip,
            user_agent=user_agent,
        )

        await self._emitir_verificacion(usuario)
        sesion = await self._emitir_sesion(usuario, ip=ip, user_agent=user_agent)
        await self.db.commit()
        return sesion

    async def registrar_fundacion(
        self, data: RegisterFundacionRequest, *, ip: str | None, user_agent: str | None
    ) -> TokenResponse:
        if not data.passwords_coinciden():
            raise ConflictError("Las contraseñas no coinciden.")

        if await self.repo.por_email_local(data.email):
            raise ConflictError(_GENERIC_REGISTER_CONFLICT)
        if data.nit and await self.repo.existe_nit(data.nit):
            raise ConflictError(_GENERIC_REGISTER_CONFLICT)

        usuario = Usuario(
            nombre=data.nombre,
            email=data.email,
            password_hash=hash_password(data.password),
            provider=PROVIDER_LOCAL,
            telefono=data.telefono,
            rol=ROL_FUNDACION,
            estado=ESTADO_ACTIVO,
            email_verificado=False,
        )
        self.repo.add(usuario)
        await self.db.flush()

        perfil = Fundacion(
            usuario_id=usuario.id,
            nombre=data.nombre_fundacion,
            nit=data.nit,
            tipo_organizacion=data.tipo_organizacion,
            constituida_legalmente=data.constituida_legalmente,
            representante_legal=data.representante_legal,
            correo_institucional=data.correo_institucional,
            telefono=data.telefono_contacto,
            direccion=data.direccion,
            municipio_id=data.municipio_id,
            descripcion=data.descripcion,
            documento_legal=data.documento_legal,
            pagina_web=data.pagina_web,
            estado_verificacion="PENDIENTE",
        )
        self.repo.add(perfil)

        await self.legal.registrar_aceptaciones(
            usuario_id=usuario.id,
            aceptaciones=data.aceptaciones,
            ip=ip,
            user_agent=user_agent,
        )

        await self._emitir_verificacion(usuario)
        sesion = await self._emitir_sesion(usuario, ip=ip, user_agent=user_agent)
        await self.db.commit()
        return sesion

    # ─────────────── Login ───────────────

    async def login(
        self, email: str, password: str, *, ip: str | None, user_agent: str | None
    ) -> TokenResponse:
        usuario = await self.repo.por_email_local(email)

        # Verificación en tiempo (casi) constante: si no hay usuario, igual gastamos
        # el costo de un verify para no filtrar por timing si existe el email.
        if usuario is None:
            verify_password(password, None)
            raise AuthError(_GENERIC_INVALID_CREDS)

        if not verify_password(password, usuario.password_hash):
            raise AuthError(_GENERIC_INVALID_CREDS)

        if usuario.estado == ESTADO_BLOQUEADO:
            raise AuthError("Tu cuenta está bloqueada. Contacta al soporte.")
        if usuario.estado == ESTADO_SUSPENDIDO:
            raise AuthError("Tu cuenta está suspendida. Contacta al soporte.")

        # Rehash perezoso: migra bcrypt -> Argon2id tras login exitoso.
        if needs_rehash(usuario.password_hash):
            usuario.password_hash = hash_password(password)

        sesion = await self._emitir_sesion(usuario, ip=ip, user_agent=user_agent)
        await self.db.commit()
        return sesion

    # ─────────────── Refresh / logout ───────────────

    async def refresh(
        self, refresh_token: str, *, ip: str | None, user_agent: str | None
    ) -> TokenResponse:
        usuario_id = await self.tokens.consumir_refresh_token(refresh_token)
        if usuario_id is None:
            raise AuthError("Refresh token inválido o expirado.")

        usuario = await self.repo.por_id(usuario_id)
        if usuario is None or usuario.estado != ESTADO_ACTIVO:
            await self.db.commit()  # persiste la marca de usado
            raise AuthError("Sesión no válida.")

        sesion = await self._emitir_sesion(usuario, ip=ip, user_agent=user_agent)
        await self.db.commit()
        # refresh no reenvía el usuario en el contrato del móvil, pero no estorba.
        return sesion

    async def logout(self, usuario_id) -> None:  # noqa: ANN001
        await self.tokens.revocar_refresh_tokens(usuario_id)
        await self.db.commit()

    async def revocar_refresh(self, usuario_id) -> int:  # noqa: ANN001
        count = await self.tokens.revocar_refresh_tokens(usuario_id)
        await self.db.commit()
        return count

    # ─────────────── Verificación de email ───────────────

    async def _emitir_verificacion(self, usuario: Usuario) -> None:
        from app.email.mailer import Mailer

        raw = await self.tokens.emitir_token_verificacion(usuario.id)
        enlace = f"{self.settings.frontend_verify_url}?token={raw}"
        Mailer(self.settings).send(
            to=usuario.email,
            subject="Verifica tu correo en Solari",
            body=(
                f"Hola {usuario.nombre},\n\n"
                f"Confirma tu correo visitando: {enlace}\n\n"
                "Si no creaste esta cuenta, ignora este mensaje."
            ),
        )

    async def verificar_email(self, raw_token: str) -> bool:
        usuario_id = await self.tokens.consumir_token_verificacion(raw_token)
        if usuario_id is None:
            await self.db.commit()
            return False
        usuario = await self.repo.por_id(usuario_id)
        if usuario:
            usuario.email_verificado = True
        await self.db.commit()
        return True

    # ─────────────── Reset de contraseña ───────────────

    async def solicitar_reset(self, email: str, *, ip: str | None, user_agent: str | None) -> None:
        """Siempre responde igual (no enumerable). Solo envía correo si existe."""
        from app.email.mailer import Mailer

        usuario = await self.repo.por_email_local(email)
        if usuario is None:
            return
        raw = await self.tokens.emitir_token_reset(usuario.id, ip=ip, user_agent=user_agent)
        enlace = f"{self.settings.frontend_reset_url}?token={raw}"
        Mailer(self.settings).send(
            to=usuario.email,
            subject="Restablece tu contraseña de Solari",
            body=(
                f"Hola {usuario.nombre},\n\n"
                f"Para crear una contraseña nueva visita: {enlace}\n\n"
                "El enlace caduca en 1 hora y solo puede usarse una vez.\n"
                "Si no solicitaste esto, ignora este mensaje."
            ),
        )
        await self.db.commit()

    async def reset_password(self, raw_token: str, nueva_password: str) -> bool:
        usuario_id = await self.tokens.consumir_token_reset(raw_token)
        if usuario_id is None:
            await self.db.commit()
            return False
        usuario = await self.repo.por_id(usuario_id)
        if usuario is None:
            await self.db.commit()
            return False
        usuario.password_hash = hash_password(nueva_password)
        # Revoca todas las sesiones activas tras cambiar la contraseña.
        await self.tokens.revocar_refresh_tokens(usuario.id)
        await self.db.commit()
        return True
