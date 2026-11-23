"""Siembra idempotente del catálogo de intereses del voluntario (~30).

Añade los intereses que falten por nombre, sin duplicar los existentes.
Uso:  uv run python scripts/seed_intereses.py
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select  # noqa: E402

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.gamificacion import Interes  # noqa: E402

INTERESES = [
    "Protección animal",
    "Medio ambiente",
    "Reforestación",
    "Educación",
    "Alfabetización",
    "Infancia",
    "Adultos mayores",
    "Salud y bienestar",
    "Inclusión social",
    "Población vulnerable",
    "Seguridad alimentaria",
    "Derechos humanos",
    "Cultura y arte",
    "Deporte",
    "Recreación",
    "Tecnología",
    "Innovación social",
    "Ciencia",
    "Desarrollo comunitario",
    "Construcción de vivienda",
    "Atención de emergencias",
    "Gestión de riesgos",
    "Limpieza de espacios públicos",
    "Protección de recursos hídricos",
    "Agricultura sostenible",
    "Acompañamiento psicológico",
    "Enseñanza de idiomas",
    "Turismo comunitario",
    "Emprendimiento social",
    "Movilidad y accesibilidad",
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        existentes = {
            n.lower()
            for n in (await db.execute(select(Interes.nombre))).scalars().all()
        }
        nuevos = 0
        for nombre in INTERESES:
            if nombre.lower() not in existentes:
                db.add(Interes(nombre=nombre))
                nuevos += 1
        await db.commit()
        total = (await db.execute(select(Interes))).scalars().all()
        print(f"Intereses añadidos: {nuevos}. Total en catálogo: {len(total)}")


if __name__ == "__main__":
    # psycopg async en Windows necesita SelectorEventLoop (el Proactor no sirve).
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())
