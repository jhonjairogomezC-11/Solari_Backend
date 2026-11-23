"""Siembra idempotente de objetos y servicios de ejemplo (publicaciones de voluntarios).

Usa los voluntarios y municipios que ya existan en la base. No duplica por título.
Uso:  uv run python scripts/seed_ofrecimientos.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import insert, select  # noqa: E402

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.catalogo import Habilidad, Municipio  # noqa: E402
from app.models.ofrecimiento import (  # noqa: E402
    OF_DISPONIBLE,
    TIPO_OBJETO,
    TIPO_SERVICIO,
    Ofrecimiento,
    ofrecimiento_habilidades,
)
from app.models.voluntario import Voluntario  # noqa: E402

OBJETOS = [
    ("Libros infantiles de cuentos", "Libros y material educativo", 12, "COMO_NUEVO",
     "Colección de 12 cuentos ilustrados para niños de 4 a 9 años, ideales para una biblioteca comunitaria."),
    ("Ropa de abrigo para adultos", "Ropa y calzado", 20, "USADO_BUEN_ESTADO",
     "Chaquetas, buzos y ruanas limpias y en buen estado, tallas S a XL."),
    ("Alimento seco para perros", "Alimento para animales", 8, "NUEVO",
     "Ocho bultos de 2 kg de concentrado para perro adulto, sellados y con vencimiento lejano."),
    ("Juguetes didácticos", "Juguetes", 15, "USADO_BUEN_ESTADO",
     "Rompecabezas, bloques y juegos de mesa completos para ludotecas o jardines."),
    ("Kit de herramientas básicas", "Herramientas", 3, "USADO_BUEN_ESTADO",
     "Martillo, destornilladores, alicates y metro, útiles para jornadas de reparación."),
    ("Mesas y sillas plásticas", "Muebles y hogar", 6, "USADO",
     "Seis juegos de mesa con cuatro sillas, aptos para comedores comunitarios."),
]

SERVICIOS = [
    ("Pintura de fachadas y salones", "Pintura",
     "Ofrezco mano de obra para pintar salones, fachadas o muros de fundaciones.",
     "Fines de semana, 8:00 a. m. a 4:00 p. m.", "Hasta 80 m² por jornada. La pintura la aporta la organización."),
    ("Tutorías de matemáticas y física", "Tutorías y enseñanza",
     "Refuerzo escolar para primaria y bachillerato, de forma individual o grupal.",
     "Martes y jueves en la tarde", "Grupos de máximo 8 niños. Sesiones de 1 hora."),
    ("Diseño de logos y piezas gráficas", "Diseño gráfico",
     "Diseño de logo, afiches y publicaciones para redes de tu organización.",
     "Flexible, entrega en 5 días hábiles", "Hasta 3 piezas por organización."),
    ("Revisión veterinaria básica", "Veterinaria",
     "Jornada de valoración, desparasitación y orientación para animales rescatados.",
     "Un sábado al mes", "Los medicamentos los aporta la organización."),
    ("Soporte técnico de computadores", "Tecnología y soporte",
     "Mantenimiento, instalación de software y configuración de redes sencillas.",
     "Entre semana en la noche", "Atención presencial o remota."),
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        vols = list((await db.execute(select(Voluntario).limit(3))).scalars().all())
        if not vols:
            print("No hay voluntarios en la base; crea al menos uno antes de sembrar.")
            return
        municipios = [m for (m,) in (await db.execute(select(Municipio.id).limit(5))).all()]
        habilidades = [h for (h,) in (await db.execute(select(Habilidad.id).limit(3))).all()]
        existentes = set((await db.execute(select(Ofrecimiento.titulo))).scalars().all())
        nuevos = 0

        for i, (titulo, cat, cant, estado, desc) in enumerate(OBJETOS):
            if titulo in existentes:
                continue
            db.add(Ofrecimiento(
                voluntario_id=vols[i % len(vols)].id,
                tipo=TIPO_OBJETO, titulo=titulo, descripcion=desc, categoria=cat,
                cantidad_total=cant, cantidad_disponible=cant,
                estado_producto=estado,
                modalidad_entrega=("RECOGER_EN_LUGAR", "ENTREGA_POR_VOLUNTARIO", "A_CONVENIR")[i % 3],
                municipio_id=municipios[i % len(municipios)] if municipios else None,
                fecha_vencimiento=date.today() + timedelta(days=90),
                imagenes=[], estado=OF_DISPONIBLE,
            ))
            nuevos += 1

        servicios_nuevos = []
        for i, (titulo, cat, desc, disp, alcance) in enumerate(SERVICIOS):
            if titulo in existentes:
                continue
            of = Ofrecimiento(
                voluntario_id=vols[(i + 1) % len(vols)].id,
                tipo=TIPO_SERVICIO, titulo=titulo, descripcion=desc, categoria=cat,
                cantidad_total=1, cantidad_disponible=1,
                municipio_id=municipios[i % len(municipios)] if municipios else None,
                disponibilidad=disp, alcance=alcance,
                condiciones="Servicio gratuito. Se coordina por mensajes dentro de la plataforma.",
                imagenes=[], estado=OF_DISPONIBLE,
            )
            db.add(of)
            servicios_nuevos.append(of)
            nuevos += 1

        await db.flush()
        for of in servicios_nuevos:
            for hid in habilidades[:2]:
                await db.execute(
                    insert(ofrecimiento_habilidades).values(ofrecimiento_id=of.id, habilidad_id=hid)
                )
        await db.commit()
        print(f"Publicaciones añadidas: {nuevos}")


if __name__ == "__main__":
    asyncio.run(main())
