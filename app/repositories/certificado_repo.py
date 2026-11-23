"""Acceso a datos para certificados de participación."""

from __future__ import annotations

import uuid
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fundacion import Fundacion
from app.models.postulacion import Postulacion
from app.models.publicacion import Publicacion
from app.models.usuario import Usuario
from app.models.voluntario import Voluntario


class FilaCertificado(NamedTuple):
    postulacion: Postulacion
    publicacion: Publicacion
    fundacion: Fundacion
    voluntario: Voluntario
    usuario: Usuario


class CertificadoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def datos_postulacion(self, postulacion_id: uuid.UUID) -> FilaCertificado | None:
        """Postulación con su convocatoria, organización, voluntario y usuario."""
        stmt = (
            select(Postulacion, Publicacion, Fundacion, Voluntario, Usuario)
            .join(Publicacion, Publicacion.id == Postulacion.publicacion_id)
            .join(Fundacion, Fundacion.id == Publicacion.fundacion_id)
            .join(Voluntario, Voluntario.id == Postulacion.voluntario_id)
            .join(Usuario, Usuario.id == Voluntario.usuario_id)
            .where(Postulacion.id == postulacion_id)
        )
        fila = (await self.db.execute(stmt)).one_or_none()
        if fila is None:
            return None
        return FilaCertificado(*fila)
