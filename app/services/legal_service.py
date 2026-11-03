"""Servicio de documentos legales y registro de aceptaciones.

Reglas de seguridad:
- El cliente solo indica QUÉ documento acepta (por código). El backend resuelve la
  versión vigente y sella la fecha del lado servidor. El cliente no puede inventar
  versión ni fecha.
- Durante el registro, todos los documentos con `requerido_registro=True` deben
  aceptarse; de lo contrario se rechaza la creación de la cuenta.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.legal import (
    DocumentoLegal,
    DocumentoLegalVersion,
    UsuarioAceptacionLegal,
)
from app.schemas.auth import AceptacionLegalInput


class LegalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def documentos_vigentes(self) -> list[tuple[DocumentoLegal, DocumentoLegalVersion]]:
        stmt = (
            select(DocumentoLegal, DocumentoLegalVersion)
            .join(DocumentoLegalVersion, DocumentoLegalVersion.documento_id == DocumentoLegal.id)
            .where(DocumentoLegalVersion.vigente.is_(True))
            .order_by(DocumentoLegal.codigo)
        )
        rows = (await self.db.execute(stmt)).all()
        return [(doc, ver) for doc, ver in rows]

    async def _version_vigente_por_codigo(self, codigo: str) -> DocumentoLegalVersion | None:
        stmt = (
            select(DocumentoLegalVersion)
            .join(DocumentoLegal, DocumentoLegal.id == DocumentoLegalVersion.documento_id)
            .where(DocumentoLegal.codigo == codigo, DocumentoLegalVersion.vigente.is_(True))
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _codigos_requeridos(self) -> set[str]:
        stmt = select(DocumentoLegal.codigo).where(
            DocumentoLegal.requerido_registro.is_(True)
        )
        return {c for (c,) in (await self.db.execute(stmt)).all()}

    async def registrar_aceptaciones(
        self,
        *,
        usuario_id: uuid.UUID,
        aceptaciones: list[AceptacionLegalInput],
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        """Valida que se aceptaron los documentos requeridos y guarda la evidencia.

        Si no existen documentos legales cargados aún, no bloquea el registro
        (fase inicial sin contenido jurídico). En cuanto se publique un documento
        requerido, su aceptación pasa a ser obligatoria.
        """
        requeridos = await self._codigos_requeridos()
        aceptados_codigos = {a.codigo for a in aceptaciones if a.aceptado}

        faltantes = requeridos - aceptados_codigos
        if faltantes:
            raise ConflictError(
                "Debes aceptar los documentos legales requeridos: " + ", ".join(sorted(faltantes))
            )

        for ac in aceptaciones:
            if not ac.aceptado:
                continue
            version = await self._version_vigente_por_codigo(ac.codigo)
            if version is None:
                # Documento desconocido o sin versión vigente: se ignora silenciosamente
                # salvo que fuese requerido (ya validado arriba).
                continue
            self.db.add(
                UsuarioAceptacionLegal(
                    usuario_id=usuario_id,
                    version_id=version.id,
                    aceptado=True,
                    ip_aceptacion=ip,
                    user_agent=user_agent,
                )
            )
