"""Acceso a datos de usuarios y perfiles. Todo vía ORM (consultas parametrizadas)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fundacion import Fundacion
from app.models.usuario import PROVIDER_LOCAL, Usuario
from app.models.voluntario import Voluntario


class UsuarioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def por_email_provider(self, email: str, provider: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.email == email, Usuario.provider == provider)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def por_email_local(self, email: str) -> Usuario | None:
        return await self.por_email_provider(email, PROVIDER_LOCAL)

    async def por_provider_id(self, provider: str, provider_id: str) -> Usuario | None:
        stmt = select(Usuario).where(
            Usuario.provider == provider, Usuario.provider_id == provider_id
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def por_id(self, usuario_id: str | uuid.UUID) -> Usuario | None:
        return await self.db.get(Usuario, usuario_id)

    async def existe_numero_documento(self, numero: str) -> bool:
        stmt = select(Voluntario.id).where(Voluntario.numero_documento == numero)
        return (await self.db.execute(stmt)).first() is not None

    async def existe_nit(self, nit: str) -> bool:
        stmt = select(Fundacion.id).where(Fundacion.nit == nit)
        return (await self.db.execute(stmt)).first() is not None

    def add(self, entidad: object) -> None:
        self.db.add(entidad)
