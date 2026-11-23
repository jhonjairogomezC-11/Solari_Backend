"""Entrega autenticada de documentos privados (identidad y verificación)."""

from __future__ import annotations

import re

from fastapi import APIRouter
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.models.fundacion import Fundacion
from app.models.organizacion import FundacionDocumento
from app.models.usuario import ROL_ADMIN
from app.models.voluntario import Voluntario
from app.services.storage_service import CARPETAS_PRIVADAS, PRIVADO_PREFIJO, StorageService

router = APIRouter(prefix="/archivos", tags=["archivos"])

_NOMBRE_VALIDO = re.compile(r"^[A-Za-z0-9_-]{8,64}\.(pdf|jpg|png|webp|gif)$")
_MEDIA = {
    "pdf": "application/pdf", "jpg": "image/jpeg", "png": "image/png",
    "webp": "image/webp", "gif": "image/gif",
}


@router.get("/privado/{carpeta}/{nombre}")
async def descargar_privado(carpeta: str, nombre: str, db: DbDep, user: CurrentUser):
    """Sirve un documento privado solo a su dueño o a un administrador.

    Cualquier otro caso responde 404 (no revela si el archivo existe).
    """
    if carpeta not in CARPETAS_PRIVADAS or not _NOMBRE_VALIDO.fullmatch(nombre):
        raise NotFoundError("Archivo no encontrado.")
    referencia = f"{PRIVADO_PREFIJO}/{carpeta}/{nombre}"

    autorizado = user.rol == ROL_ADMIN
    if not autorizado:
        vol = (
            await db.execute(
                select(Voluntario.usuario_id).where(Voluntario.documento_identidad == referencia)
            )
        ).scalar_one_or_none()
        if vol is not None and vol == user.id:
            autorizado = True
    if not autorizado:
        dueno = (
            await db.execute(
                select(Fundacion.usuario_id)
                .join(FundacionDocumento, FundacionDocumento.fundacion_id == Fundacion.id)
                .where(FundacionDocumento.ruta_archivo == referencia)
            )
        ).scalar_one_or_none()
        if dueno is not None and dueno == user.id:
            autorizado = True
    if not autorizado:
        raise NotFoundError("Archivo no encontrado.")

    ruta = StorageService(get_settings()).ruta_privada(carpeta, nombre)
    if not ruta.is_file():
        raise NotFoundError("Archivo no encontrado.")
    return FileResponse(
        ruta,
        media_type=_MEDIA[nombre.rsplit(".", 1)[1]],
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
