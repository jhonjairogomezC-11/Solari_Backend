"""Seguridad de cuenta: sesiones activas, alertas de inicio de sesión y MFA (TOTP).

- Una "sesión" es un refresh token vigente (no usado/revocado y no expirado). Al
  rotar, el nuevo token conserva `fecha_inicio_sesion` y el dispositivo.
- La sesión actual se identifica comparando el hash SHA-256 del refresh token que
  envía el cliente (cabecera `X-Refresh-Token`) con `token_hash`. Nunca se
  devuelven valores ni hashes de tokens.
- Las alertas se crean como notificación CUENTA_ACTUALIZADA (siempre se entregan).
  Un fallo al crear la alerta nunca impide iniciar sesión (savepoint).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import exists, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import mfa
from app.core.config import Settings
from app.core.exceptions import AppError, AuthError, ConflictError, NotFoundError
from app.core.security import hash_opaque_token, verify_password
from app.models.notificacion import TIPO_CUENTA_ACTUALIZADA
from app.models.tokens import RefreshToken
from app.models.usuario import PROVIDER_LOCAL, ROL_ADMIN, Usuario
from app.schemas.seguridad import (
    MfaConfirmarOut,
    MfaEstadoOut,
    MfaIniciarOut,
    SesionOut,
)

logger = logging.getLogger("solari.seguridad")

_CODIGO_INVALIDO = "El código no es válido o ya fue usado."


def _now() -> datetime:
    return datetime.now(UTC)


# ─────────────────────────── Alertas ───────────────────────────


async def notificar_seguro(db: AsyncSession, usuario_id: uuid.UUID, mensaje: str) -> None:
    """Crea una notificación CUENTA_ACTUALIZADA sin romper la transacción si falla."""
    from app.services.notificacion_service import NotificacionService

    try:
        async with db.begin_nested():
            await NotificacionService(db).notificar(usuario_id, TIPO_CUENTA_ACTUALIZADA, mensaje)
    except SQLAlchemyError:
        logger.warning("No se pudo crear la notificación de seguridad", exc_info=True)


async def alertar_si_dispositivo_nuevo(
    db: AsyncSession, usuario: Usuario, *, ip: str | None, user_agent: str | None
) -> bool:
    """Notifica si el par (user agent, IP) no aparece en sesiones previas del usuario.

    Debe llamarse ANTES de emitir el refresh token del nuevo inicio de sesión. Si el
    usuario no tiene ninguna sesión previa (primer ingreso), no se alerta.
    """
    ua = mfa.truncar(user_agent, 255)
    ip_t = mfa.truncar(ip, 50)
    try:
        async with db.begin_nested():
            hay_previas = (
                await db.execute(select(exists().where(RefreshToken.usuario_id == usuario.id)))
            ).scalar()
            if not hay_previas:
                return False
            condiciones = [RefreshToken.usuario_id == usuario.id]
            condiciones.append(
                RefreshToken.ip_solicitud.is_(None)
                if ip_t is None
                else RefreshToken.ip_solicitud == ip_t
            )
            condiciones.append(
                RefreshToken.user_agent.is_(None)
                if ua is None
                else func.left(RefreshToken.user_agent, 255) == ua
            )
            visto = (await db.execute(select(exists().where(*condiciones)))).scalar()
    except SQLAlchemyError:
        logger.warning("No se pudo evaluar la alerta de inicio de sesión", exc_info=True)
        return False
    if visto:
        return False

    dispositivo = mfa.resumen_user_agent(user_agent)
    donde = f" (IP {ip_t})" if ip_t else ""
    mensaje = (
        f"Se inició sesión en tu cuenta de Solari desde un dispositivo nuevo: "
        f"{dispositivo}{donde}, el {mfa.fecha_bogota()} (hora de Bogotá). "
        "Si no fuiste tú, cambia tu contraseña y cierra las demás sesiones desde Seguridad."
    )
    await notificar_seguro(db, usuario.id, mensaje)
    return True


# ─────────────────────────── Sesiones ───────────────────────────


class SesionesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _activas(self, usuario_id: uuid.UUID):
        return select(RefreshToken).where(
            RefreshToken.usuario_id == usuario_id,
            RefreshToken.usado.is_(False),
            RefreshToken.expiracion > _now(),
        )

    async def listar(self, usuario_id: uuid.UUID, refresh_actual: str | None) -> list[SesionOut]:
        hash_actual = hash_opaque_token(refresh_actual) if refresh_actual else None
        filas = (
            await self.db.execute(
                self._activas(usuario_id).order_by(RefreshToken.fecha_creacion.desc())
            )
        ).scalars().all()
        sesiones = [
            SesionOut(
                id=f.id,
                dispositivo=mfa.resumen_user_agent(f.user_agent),
                ip=f.ip_solicitud,
                fecha_inicio=f.fecha_inicio_sesion or f.fecha_creacion,
                fecha_ultimo_uso=f.fecha_ultimo_uso or f.fecha_creacion,
                expiracion=f.expiracion,
                actual=bool(hash_actual and f.token_hash == hash_actual),
            )
            for f in filas
        ]
        # La sesión actual primero.
        sesiones.sort(key=lambda s: not s.actual)
        return sesiones

    async def revocar(self, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> None:
        result = await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.id == sesion_id,
                RefreshToken.usuario_id == usuario_id,  # solo sesiones propias
                RefreshToken.usado.is_(False),
            )
            .values(usado=True, fecha_uso=_now())
        )
        if not result.rowcount:
            await self.db.rollback()
            raise NotFoundError("La sesión no existe o ya fue cerrada.")
        await self.db.commit()

    async def cerrar_otras(self, usuario_id: uuid.UUID, refresh_actual: str | None) -> int:
        if not refresh_actual:
            raise AppError(
                "No se pudo identificar la sesión actual. Vuelve a iniciar sesión.", 400
            )
        hash_actual = hash_opaque_token(refresh_actual)
        actual = (
            await self.db.execute(
                self._activas(usuario_id).where(RefreshToken.token_hash == hash_actual)
            )
        ).scalar_one_or_none()
        if actual is None:
            raise AppError(
                "No se pudo identificar la sesión actual. Vuelve a iniciar sesión.", 400
            )
        result = await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.usuario_id == usuario_id,
                RefreshToken.usado.is_(False),
                RefreshToken.id != actual.id,
            )
            .values(usado=True, fecha_uso=_now())
        )
        await self.db.commit()
        return result.rowcount or 0


# ─────────────────────────── MFA (TOTP) ───────────────────────────


class MfaService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    def estado(self, usuario: Usuario) -> MfaEstadoOut:
        return MfaEstadoOut(
            activo=bool(usuario.mfa_activo),
            codigos_respaldo_restantes=len(usuario.mfa_codigos_respaldo or [])
            if usuario.mfa_activo
            else 0,
            recomendado=usuario.rol == ROL_ADMIN,
        )

    def _secreto(self, usuario: Usuario) -> str | None:
        if not usuario.mfa_secret:
            return None
        try:
            return mfa.descifrar_secreto(self.settings, usuario.mfa_secret)
        except mfa.MfaSecretError:
            logger.error("Secreto MFA ilegible para el usuario %s", usuario.id)
            return None

    async def iniciar(self, usuario: Usuario) -> MfaIniciarOut:
        if usuario.mfa_activo:
            raise ConflictError("La verificación en dos pasos ya está activa.")
        secreto = mfa.generar_secreto()
        # Queda pendiente (mfa_activo=False) hasta confirmar con un código válido.
        usuario.mfa_secret = mfa.cifrar_secreto(self.settings, secreto)
        usuario.mfa_codigos_respaldo = None
        usuario.mfa_ultimo_paso = None
        await self.db.commit()
        uri = mfa.otpauth_uri(secreto, usuario.email)
        return MfaIniciarOut(otpauth_uri=uri, qr_svg=mfa.qr_svg_data_uri(uri), secreto=secreto)

    async def confirmar(self, usuario: Usuario, codigo: str) -> MfaConfirmarOut:
        if usuario.mfa_activo:
            raise ConflictError("La verificación en dos pasos ya está activa.")
        secreto = self._secreto(usuario)
        if secreto is None:
            raise AppError("Primero inicia la configuración de la verificación en dos pasos.")
        paso = mfa.verificar_totp(secreto, codigo)
        if paso is None:
            raise AppError("El código no es válido. Revisa la hora de tu dispositivo.")
        codigos = mfa.generar_codigos_respaldo()
        usuario.mfa_codigos_respaldo = [mfa.hash_codigo_respaldo(c) for c in codigos]
        usuario.mfa_ultimo_paso = paso
        usuario.mfa_activo = True
        await notificar_seguro(
            self.db,
            usuario.id,
            f"Activaste la verificación en dos pasos el {mfa.fecha_bogota()} (hora de Bogotá).",
        )
        await self.db.commit()
        return MfaConfirmarOut(
            message="Verificación en dos pasos activada.", codigos_respaldo=codigos
        )

    async def desactivar(self, usuario: Usuario, password: str | None, codigo: str) -> None:
        if not usuario.mfa_activo:
            raise ConflictError("La verificación en dos pasos no está activa.")
        # Cuentas locales: exigen contraseña. Cuentas de Google no tienen contraseña.
        if usuario.provider == PROVIDER_LOCAL or usuario.password_hash:
            if not password or not verify_password(password, usuario.password_hash):
                raise AuthError("La contraseña no es correcta.")
        if not self.verificar_segundo_factor(usuario, codigo):
            raise AppError(_CODIGO_INVALIDO)
        usuario.mfa_activo = False
        usuario.mfa_secret = None
        usuario.mfa_codigos_respaldo = None
        usuario.mfa_ultimo_paso = None
        await notificar_seguro(
            self.db,
            usuario.id,
            f"Desactivaste la verificación en dos pasos el {mfa.fecha_bogota()} "
            "(hora de Bogotá). Si no fuiste tú, cambia tu contraseña de inmediato.",
        )
        await self.db.commit()

    def verificar_segundo_factor(self, usuario: Usuario, codigo: str) -> bool:
        """Acepta un TOTP vigente (anti-replay) o consume un código de respaldo.

        Modifica el usuario en memoria; quien llama debe hacer commit.
        """
        if not usuario.mfa_activo:
            return False
        if mfa.es_formato_totp(codigo):
            secreto = self._secreto(usuario)
            if secreto is None:
                return False
            paso = mfa.verificar_totp(secreto, codigo, ultimo_paso=usuario.mfa_ultimo_paso)
            if paso is None:
                return False
            usuario.mfa_ultimo_paso = paso
            return True
        restantes = mfa.consumir_codigo_respaldo(usuario.mfa_codigos_respaldo, codigo)
        if restantes is None:
            return False
        usuario.mfa_codigos_respaldo = restantes
        return True
