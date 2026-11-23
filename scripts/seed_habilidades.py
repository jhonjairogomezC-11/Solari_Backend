"""Siembra idempotente del catálogo de habilidades (~100) y habilidades requeridas
de las convocatorias existentes que no tienen ninguna.

Uso:  .venv\\Scripts\\python.exe scripts\\seed_habilidades.py

Las categorías siguen la sección 4.4 del documento de grado: cuidado animal,
medio ambiente, salud y bienestar, educación, apoyo social, construcción y
mantenimiento, y tecnología y comunicación. Las marcadas como profesionales
(P) requieren formación o certificación; el resto son generales o de apoyo.
"""

from __future__ import annotations

import asyncio
import random
import sys

from sqlalchemy import func, insert, select  # noqa: E402

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.catalogo import AreaImpacto, Habilidad  # noqa: E402
from app.models.publicacion import Publicacion, publicacion_habilidades  # noqa: E402

P = True  # profesional / técnica
G = False  # general / de apoyo

CATALOGO: dict[str, list[tuple[str, bool]]] = {
    "Cuidado animal": [
        ("Cuidado de perros", G), ("Cuidado de gatos", G), ("Baño de animales", G),
        ("Paseo de mascotas", G), ("Alimentación de animales", G), ("Rescate de animales", G),
        ("Apoyo en adopciones responsables", G), ("Primeros auxilios para animales", G),
        ("Apoyo en campañas de esterilización", G), ("Limpieza de refugios", G),
        ("Fotografía de mascotas en adopción", G), ("Hogar de paso", G),
        ("Medicina veterinaria", P), ("Adiestramiento canino", P),
    ],
    "Medio ambiente": [
        ("Siembra de árboles", G), ("Reforestación", G), ("Limpieza de ríos y quebradas", G),
        ("Recolección de residuos", G), ("Reciclaje y clasificación", G), ("Compostaje", G),
        ("Huertas urbanas", G), ("Educación ambiental", G), ("Restauración ecológica", G),
        ("Monitoreo de fauna y flora", G), ("Jardinería", G), ("Gestión de residuos", G),
        ("Ingeniería ambiental", P), ("Biología", P),
    ],
    "Salud y bienestar": [
        ("Primeros auxilios", G), ("Acompañamiento a adultos mayores", G),
        ("Acompañamiento hospitalario", G), ("Apoyo en jornadas de salud", G),
        ("Actividad física y recreación", G), ("Nutrición básica", G),
        ("Cuidado de personas con discapacidad", G), ("Apoyo emocional", G),
        ("Yoga y relajación", G), ("Enfermería", P), ("Psicología", P),
        ("Medicina general", P), ("Fisioterapia", P), ("Odontología", P),
    ],
    "Educación": [
        ("Refuerzo escolar", G), ("Alfabetización de adultos", G), ("Lectura en voz alta", G),
        ("Matemáticas", G), ("Ciencias naturales", G), ("Arte y manualidades", G),
        ("Música", G), ("Teatro y expresión corporal", G), ("Orientación vocacional", G),
        ("Educación financiera", G), ("Tutoría universitaria", G),
        ("Recreación formativa", G), ("Pedagogía", P), ("Educación especial", P),
    ],
    "Apoyo social": [
        ("Preparación de alimentos", G), ("Distribución de alimentos", G),
        ("Recolección de donaciones", G), ("Organización de eventos", G),
        ("Acompañamiento a niños y niñas", G), ("Atención a población vulnerable", G),
        ("Apoyo a población migrante", G), ("Liderazgo comunitario", G),
        ("Trabajo en equipo", G), ("Logística y transporte", G), ("Atención al público", G),
        ("Apoyo en emergencias", G), ("Trabajo social", P), ("Asesoría jurídica", P),
    ],
    "Construcción y mantenimiento": [
        ("Pintura", G), ("Albañilería básica", G), ("Carpintería", G),
        ("Electricidad básica", G), ("Plomería básica", G), ("Soldadura", G),
        ("Mantenimiento general", G), ("Reparación de mobiliario", G),
        ("Construcción de vivienda", G), ("Adecuación de espacios", G),
        ("Limpieza y aseo", G), ("Instalaciones eléctricas certificadas", P),
        ("Plomería certificada", P), ("Arquitectura e ingeniería civil", P),
    ],
    "Tecnología y comunicación": [
        ("Diseño gráfico", G), ("Fotografía", G), ("Edición de video", G),
        ("Gestión de redes sociales", G), ("Redacción y comunicación", G),
        ("Manejo de ofimática", G), ("Soporte técnico", G), ("Traducción", G),
        ("Locución y presentación", G), ("Gestión de proyectos", G),
        ("Marketing digital", G), ("Desarrollo web", P), ("Análisis de datos", P),
        ("Contabilidad", P),
    ],
}

# Categoría de las 10 habilidades originales (ya existían en la BD).
ORIGINALES: dict[str, str] = {
    "Educación": "Educación", "Tecnología": "Tecnología y comunicación",
    "Salud": "Salud y bienestar", "Medio Ambiente": "Medio ambiente",
    "Arte": "Educación", "Deportes": "Salud y bienestar",
    "Comunicación": "Tecnología y comunicación", "Liderazgo": "Apoyo social",
    "Idiomas": "Educación", "Cocina": "Apoyo social",
}

# Habilidades originales y categorías nuevas afines a cada área de impacto.
AREA_ORIGINALES: dict[str, list[str]] = {
    "Educacion": ["Educación", "Idiomas"], "Salud": ["Salud"],
    "Medio Ambiente": ["Medio Ambiente"], "Derechos Humanos": ["Liderazgo", "Comunicación"],
    "Infancia": ["Educación", "Arte"], "Adulto Mayor": ["Salud", "Cocina"],
    "Discapacidad": ["Salud", "Liderazgo"], "Cultura": ["Arte", "Comunicación"],
    "Deportes": ["Deportes"], "Tecnologia": ["Tecnología", "Comunicación"],
    "Inclusion Social": ["Liderazgo", "Cocina"],
}
AREA_CATEGORIAS: dict[str, list[str]] = {
    "Educacion": ["Educación"], "Salud": ["Salud y bienestar"],
    "Medio Ambiente": ["Medio ambiente", "Cuidado animal"],
    "Derechos Humanos": ["Apoyo social"], "Infancia": ["Educación", "Apoyo social"],
    "Adulto Mayor": ["Salud y bienestar", "Apoyo social"],
    "Discapacidad": ["Salud y bienestar", "Apoyo social"],
    "Cultura": ["Educación", "Tecnología y comunicación"],
    "Deportes": ["Salud y bienestar", "Educación"],
    "Tecnologia": ["Tecnología y comunicación"],
    "Inclusion Social": ["Apoyo social", "Construcción y mantenimiento"],
}


async def main() -> None:
    async with AsyncSessionLocal() as db:
        existentes = {
            h.nombre.lower(): h
            for h in (await db.execute(select(Habilidad))).scalars().all()
        }
        nuevas = 0
        for nombre, cat in ORIGINALES.items():
            h = existentes.get(nombre.lower())
            if h is not None and h.categoria is None:
                h.categoria = cat
        for categoria, items in CATALOGO.items():
            for nombre, prof in items:
                h = existentes.get(nombre.lower())
                if h is None:
                    db.add(Habilidad(nombre=nombre, categoria=categoria, es_profesional=prof))
                    nuevas += 1
                else:
                    h.categoria = h.categoria or categoria
                    h.es_profesional = prof
        await db.commit()

        todas = list((await db.execute(select(Habilidad))).scalars().all())
        por_nombre = {h.nombre: h for h in todas}
        por_categoria: dict[str, list[Habilidad]] = {}
        for h in todas:
            por_categoria.setdefault(h.categoria or "", []).append(h)

        # Habilidades requeridas para convocatorias que no tienen ninguna.
        areas = {a.id: a.nombre for a in (await db.execute(select(AreaImpacto))).scalars().all()}
        con_hab = set(
            (await db.execute(select(publicacion_habilidades.c.publicacion_id))).scalars().all()
        )
        pubs = (await db.execute(select(Publicacion.id, Publicacion.categoria_id))).all()
        asignadas = 0
        for pid, cat_id in pubs:
            if pid in con_hab:
                continue
            area = areas.get(cat_id, "")
            rng = random.Random(str(pid))  # determinista por convocatoria
            elegidas: dict[int, Habilidad] = {}
            for nombre in AREA_ORIGINALES.get(area, []):
                h = por_nombre.get(nombre)
                if h:
                    elegidas[h.id] = h
            pool = [
                h for c in AREA_CATEGORIAS.get(area, ["Apoyo social"])
                for h in por_categoria.get(c, []) if not h.es_profesional
            ]
            rng.shuffle(pool)
            objetivo = rng.randint(3, 5)
            for h in pool:
                if len(elegidas) >= objetivo:
                    break
                elegidas.setdefault(h.id, h)
            if len(elegidas) < 3:
                continue
            await db.execute(
                insert(publicacion_habilidades),
                [{"publicacion_id": pid, "habilidad_id": hid} for hid in elegidas],
            )
            asignadas += 1
        await db.commit()

        total = (await db.execute(select(func.count()).select_from(Habilidad))).scalar_one()
        print(f"Habilidades nuevas: {nuevas}. Total en catálogo: {total}.")
        print(f"Convocatorias a las que se asignaron habilidades requeridas: {asignadas}.")


if __name__ == "__main__":
    # psycopg async en Windows necesita SelectorEventLoop (el Proactor no sirve).
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())
