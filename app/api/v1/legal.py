"""Endpoints de documentos legales vigentes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbDep
from app.schemas.legal import DocumentoLegalVigenteOut
from app.services.legal_service import LegalService

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/documentos", response_model=list[DocumentoLegalVigenteOut])
async def documentos_vigentes(db: DbDep) -> list[DocumentoLegalVigenteOut]:
    service = LegalService(db)
    resultado = await service.documentos_vigentes()
    return [
        DocumentoLegalVigenteOut(
            codigo=doc.codigo,
            nombre=doc.nombre,
            descripcion=doc.descripcion,
            requerido_registro=doc.requerido_registro,
            version=ver.version,
            version_id=ver.id,
            url_publica=ver.url_publica,
            contenido=ver.contenido,
            fecha_publicacion=ver.fecha_publicacion,
        )
        for doc, ver in resultado
    ]
