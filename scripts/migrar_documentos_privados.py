"""Mueve los documentos de identidad antiguos (carpeta pública) al almacenamiento privado.

Antes los documentos se guardaban en `uploads/documentos` y se servían por una URL
pública. Ahora viven en `private_uploads/documentos` y solo los entrega
`/archivos/privado/...` a su dueño o a un administrador (regla R10).

Idempotente. Uso:  .venv\\Scripts\\python.exe scripts\\migrar_documentos_privados.py
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.voluntario import Voluntario  # noqa: E402


async def main() -> None:
    settings = get_settings()
    origen = Path(settings.upload_dir) / "documentos"
    destino = Path(settings.private_upload_dir) / "documentos"
    destino.mkdir(parents=True, exist_ok=True)
    movidos = sin_archivo = 0
    async with AsyncSessionLocal() as db:
        filas = (
            await db.execute(
                select(Voluntario).where(
                    Voluntario.documento_identidad.is_not(None),
                    ~Voluntario.documento_identidad.like("/archivos/privado/%"),
                )
            )
        ).scalars().all()
        for vol in filas:
            nombre = vol.documento_identidad.rstrip("/").split("/")[-1]
            archivo = origen / nombre
            if archivo.is_file():
                shutil.move(str(archivo), str(destino / nombre))
                vol.documento_identidad = f"/archivos/privado/documentos/{nombre}"
                movidos += 1
            else:
                sin_archivo += 1
        await db.commit()
    print(f"Documentos movidos a almacenamiento privado: {movidos}.")
    print(f"Referencias sin archivo en disco (se dejan como están): {sin_archivo}.")


if __name__ == "__main__":
    # psycopg async en Windows necesita SelectorEventLoop (el Proactor no sirve).
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())
