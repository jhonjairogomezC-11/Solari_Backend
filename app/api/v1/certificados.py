"""Endpoints de certificados de participación (descarga y verificación pública)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from app.api.deps import DbDep, SettingsDep, get_voluntario_actual
from app.core.rate_limit import limiter
from app.models.voluntario import Voluntario
from app.schemas.certificado import VerificacionCertificadoOut
from app.services.certificado_service import CertificadoService

router = APIRouter(tags=["certificados"])

VoluntarioDep = Annotated[Voluntario, Depends(get_voluntario_actual)]


@router.get(
    "/postulaciones/{postulacion_id}/certificado",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def descargar_certificado(
    db: DbDep,
    settings: SettingsDep,
    voluntario: VoluntarioDep,
    postulacion_id: uuid.UUID,
) -> Response:
    pdf, nombre = await CertificadoService(db, settings).certificado_pdf(
        postulacion_id, voluntario
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/certificados/verificar", response_model=VerificacionCertificadoOut)
@limiter.limit("30/minute")
async def verificar_certificado(
    request: Request,
    db: DbDep,
    settings: SettingsDep,
    postulacion: Annotated[str, Query(max_length=64)],
    codigo: Annotated[str, Query(max_length=32)],
) -> VerificacionCertificadoOut:
    """Verificación pública (sin sesión). Solo expone nombre abreviado y datos de la actividad."""
    return await CertificadoService(db, settings).verificar(postulacion, codigo)
