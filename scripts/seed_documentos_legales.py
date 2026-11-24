"""Publica los documentos legales (Términos y Política de datos) desde docs/legal/.

Uso:  .venv\\Scripts\\python.exe scripts\\seed_documentos_legales.py [--version 1.0] [--opcional]

- Idempotente: si la versión ya existe con el mismo contenido, no hace nada.
- Si la versión existe con contenido distinto y NADIE la ha aceptado, la actualiza.
- Si alguien ya la aceptó, se niega: hay que publicar una versión nueva (--version 1.1),
  para que la evidencia de aceptación siga apuntando al texto exacto que se aceptó.
- La versión publicada queda como única vigente del documento.
- Por defecto los documentos quedan como REQUERIDOS en el registro. Con --opcional, no.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

from sqlalchemy import func, select, update

from app.db.session import AsyncSessionLocal
from app.models.legal import (
    DOC_PRIVACIDAD,
    DOC_TERMINOS,
    DocumentoLegal,
    DocumentoLegalVersion,
    UsuarioAceptacionLegal,
)

DOCS = Path(__file__).resolve().parents[1] / "docs" / "legal"

DOCUMENTOS = [
    (
        DOC_TERMINOS,
        "Términos y Condiciones de Uso",
        "Reglas de uso de la plataforma para voluntarios y organizaciones.",
        "terminos_y_condiciones.md",
        "/terminos",
    ),
    (
        DOC_PRIVACIDAD,
        "Política de Tratamiento de Datos Personales",
        "Cómo Solari recoge, usa, protege y conserva los datos personales (Ley 1581 de 2012).",
        "politica_tratamiento_datos.md",
        "/privacidad",
    ),
]


async def main(version: str, requerido: bool) -> int:
    async with AsyncSessionLocal() as db:
        for codigo, nombre, descripcion, archivo, url in DOCUMENTOS:
            contenido = (DOCS / archivo).read_text(encoding="utf-8")
            digest = hashlib.sha256(contenido.encode("utf-8")).hexdigest()

            doc = (
                await db.execute(select(DocumentoLegal).where(DocumentoLegal.codigo == codigo))
            ).scalar_one_or_none()
            if doc is None:
                doc = DocumentoLegal(codigo=codigo, nombre=nombre, descripcion=descripcion)
                db.add(doc)
                await db.flush()
            doc.nombre, doc.descripcion, doc.requerido_registro = nombre, descripcion, requerido

            ver = (
                await db.execute(
                    select(DocumentoLegalVersion).where(
                        DocumentoLegalVersion.documento_id == doc.id,
                        DocumentoLegalVersion.version == version,
                    )
                )
            ).scalar_one_or_none()

            if ver is not None and ver.contenido_hash != digest:
                aceptaciones = (
                    await db.execute(
                        select(func.count()).where(UsuarioAceptacionLegal.version_id == ver.id)
                    )
                ).scalar_one()
                if aceptaciones:
                    print(
                        f"[{codigo}] La versión {version} ya tiene {aceptaciones} aceptación(es) "
                        f"y su contenido cambió. Publica una versión nueva con --version."
                    )
                    await db.rollback()
                    return 1
                ver.contenido, ver.contenido_hash = contenido, digest
                estado = "actualizada"
            elif ver is None:
                ver = DocumentoLegalVersion(
                    documento_id=doc.id,
                    version=version,
                    contenido=contenido,
                    contenido_hash=digest,
                    url_publica=url,
                )
                db.add(ver)
                await db.flush()
                estado = "publicada"
            else:
                estado = "sin cambios"

            # Solo una versión vigente por documento.
            await db.execute(
                update(DocumentoLegalVersion)
                .where(DocumentoLegalVersion.documento_id == doc.id)
                .values(vigente=DocumentoLegalVersion.id == ver.id)
            )
            print(f"[{codigo}] versión {version}: {estado}. Requerido en registro: {requerido}.")
        await db.commit()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="1.0")
    parser.add_argument("--opcional", action="store_true", help="No exigirlos en el registro.")
    args = parser.parse_args()
    corrida = main(args.version, requerido=not args.opcional)
    # psycopg async en Windows necesita SelectorEventLoop (el Proactor no sirve).
    if sys.platform == "win32":
        codigo_salida = asyncio.run(corrida, loop_factory=asyncio.SelectorEventLoop)
    else:
        codigo_salida = asyncio.run(corrida)
    sys.exit(codigo_salida)
