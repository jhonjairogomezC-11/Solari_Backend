"""Gestión de tokens opacos: refresh, reset de contraseña y verificación de email.

Todos los tokens se almacenan hasheados (SHA-256). El valor en claro se devuelve
una sola vez a quien lo solicita. Se escribe tanto `token` (compat Laravel) como
`token_hash`; la búsqueda del lado Python se hace SIEMPRE por `token_hash`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import generate_opaque_token, hash_opaque_token
from app.models.tokens import RecuperacionPassword, RefreshToken, VerificacionEmail


def _now() -> datetime:
    return datetime.now(UTC)


class TokenService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    # ─────────────── Refresh tokens ───────────────

    async def emitir_refresh_token(
        self, usuario_id: uuid.UUID, *, ip: str | None = None, user_agent: str | None = None
    ) -> str:
        raw = generate_opaque_token()
        self.db.add(
            RefreshToken(
                usuario_id=usuario_id,
                token=None,
                token_hash=hash_opaque_token(raw),
                expiracion=_now() + timedelta(minutes=self.settings.jwt_refresh_ttl_minutes),
                usado=False,
                ip_solicitud=ip,
                user_agent=user_agent,
            )
        )
        return raw

    async def consumir_refresh_token(self, raw: str) -> uuid.UUID | None:
        """Valida y marca como usado (rotación). Devuelve el usuario_id o None."""
        th = hash_opaque_token(raw)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == th,
            RefreshToken.usado.is_(False),
            RefreshToken.expiracion > _now(),
        )
        registro = (await self.db.execute(stmt)).scalar_one_or_none()
        if registro is None:
            return None
        registro.usado = True
        registro.fecha_uso = _now()
        return registro.usuario_id

    async def revocar_refresh_tokens(self, usuario_id: uuid.UUID) -> int:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.usuario_id == usuario_id, RefreshToken.usado.is_(False))
            .values(usado=True, fecha_uso=_now())
        )
        result = await self.db.execute(stmt)
        return result.rowcount or 0

    # ─────────────── Reset de contraseña ───────────────

    async def emitir_token_reset(
        self, usuario_id: uuid.UUID, *, ip: str | None, user_agent: str | None
    ) -> str:
        # Invalida tokens de reset previos sin usar.
        await self.db.execute(
            update(RecuperacionPassword)
            .where(
                RecuperacionPassword.usuario_id == usuario_id,
                RecuperacionPassword.usado.is_(False),
            )
            .values(usado=True, fecha_uso=_now())
        )
        raw = generate_opaque_token()
        self.db.add(
            RecuperacionPassword(
                usuario_id=usuario_id,
                token=None,
                token_hash=hash_opaque_token(raw),
                expiracion=_now() + timedelta(hours=1),
                usado=False,
                intentos=0,
                ip_solicitud=ip,
                user_agent=user_agent,
            )
        )
        return raw

    async def consumir_token_reset(self, raw: str) -> uuid.UUID | None:
        th = hash_opaque_token(raw)
        stmt = select(RecuperacionPassword).where(
            RecuperacionPassword.token_hash == th,
            RecuperacionPassword.usado.is_(False),
            RecuperacionPassword.expiracion > _now(),
        )
        registro = (await self.db.execute(stmt)).scalar_one_or_none()
        if registro is None:
            return None
        registro.usado = True
        registro.fecha_uso = _now()
        return registro.usuario_id

    # ─────────────── Verificación de email ───────────────

    async def emitir_token_verificacion(self, usuario_id: uuid.UUID) -> str:
        raw = generate_opaque_token()
        self.db.add(
            VerificacionEmail(
                usuario_id=usuario_id,
                token=None,
                token_hash=hash_opaque_token(raw),
                expiracion=_now() + timedelta(hours=24),
                usado=False,
            )
        )
        return raw

    async def consumir_token_verificacion(self, raw: str) -> uuid.UUID | None:
        th = hash_opaque_token(raw)
        stmt = select(VerificacionEmail).where(
            VerificacionEmail.token_hash == th,
            VerificacionEmail.usado.is_(False),
            VerificacionEmail.expiracion > _now(),
        )
        registro = (await self.db.execute(stmt)).scalar_one_or_none()
        if registro is None:
            return None
        registro.usado = True
        return registro.usuario_id
