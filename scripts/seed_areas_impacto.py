"""Siembra idempotente del catálogo de áreas de impacto (~30).

Corrige la ortografía de las áreas originales (sin tildes) y añade las que falten.
Uso:  uv run python scripts/seed_areas_impacto.py
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select  # noqa: E402

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.catalogo import AreaImpacto  # noqa: E402

# Nombre original -> nombre con ortografía correcta.
RENOMBRAR = {
    "Educacion": "Educación",
    "Inclusion Social": "Inclusión Social",
    "Tecnologia": "Tecnología",
}

AREAS = [
    "Adulto Mayor", "Cultura", "Deportes", "Derechos Humanos", "Discapacidad",
    "Educación", "Inclusión Social", "Infancia", "Medio Ambiente", "Salud", "Tecnología",
    "Protección Animal", "Reforestación y Conservación", "Gestión del Agua",
    "Seguridad Alimentaria", "Juventud", "Equidad de Género", "Población Migrante",
    "Víctimas del Conflicto y Paz", "Pueblos Indígenas y Afrodescendientes",
    "Población Rural y Campesina", "Habitantes de Calle", "Vivienda y Hábitat",
    "Emergencias y Gestión del Riesgo", "Salud Mental", "Emprendimiento y Empleo",
    "Alfabetización y Lectura", "Arte y Recreación", "Reciclaje y Economía Circular",
    "Movilidad y Accesibilidad", "Voluntariado Corporativo", "Comunidad y Barrios",
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        filas = list((await db.execute(select(AreaImpacto))).scalars().all())
        por_nombre = {a.nombre.lower(): a for a in filas}
        renombradas = 0
        for viejo, nuevo in RENOMBRAR.items():
            a = por_nombre.get(viejo.lower())
            if a and nuevo.lower() not in por_nombre:
                a.nombre = nuevo
                por_nombre.pop(viejo.lower())
                por_nombre[nuevo.lower()] = a
                renombradas += 1
        nuevas = 0
        for nombre in AREAS:
            if nombre.lower() not in por_nombre:
                db.add(AreaImpacto(nombre=nombre))
                nuevas += 1
        await db.commit()
        print(f"Áreas renombradas: {renombradas}. Áreas añadidas: {nuevas}.")


if __name__ == "__main__":
    # psycopg async en Windows necesita SelectorEventLoop (el Proactor no sirve).
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())
