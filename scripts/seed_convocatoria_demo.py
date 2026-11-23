"""Siembra una convocatoria de ejemplo completa (con galería) para «Fundacion Demo 1».

Requiere las fotos en uploads/convocatorias/reforestacion-01..05.jpg y el área de impacto
«Reforestación y Conservación» (scripts/seed_areas_impacto.py). Es idempotente por título.
Uso:  uv run python scripts/seed_convocatoria_demo.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, time

from sqlalchemy import insert, or_, select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.catalogo import AreaImpacto, Habilidad, Municipio  # noqa: E402
from app.models.fundacion import Fundacion  # noqa: E402
from app.models.gamificacion import PublicacionImagen  # noqa: E402
from app.models.publicacion import Publicacion, publicacion_habilidades  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402

TITULO = "Gran jornada de siembra de árboles nativos en los Cerros Orientales"

DESCRIPCION = (
    "Te invitamos a sembrar el futuro de Bogotá con nosotros. Durante una mañana plantaremos "
    "más de 500 árboles nativos (alisos, encenillos, mortiños y arrayanes) en una zona de los "
    "Cerros Orientales afectada por la erosión y por incendios forestales recientes.\n\n"
    "No necesitas experiencia: un equipo de ingenieros forestales te enseñará cómo preparar el "
    "terreno, abrir el hoyo, ubicar la plántula y protegerla. Trabajaremos en grupos pequeños y "
    "al final compartiremos un almuerzo para conversar sobre cómo cuidar lo que sembramos."
)

DATOS = {
    "objetivo": (
        "Recuperar 1,5 hectáreas de bosque altoandino sembrando especies nativas que protejan "
        "el suelo, conserven el agua de la quebrada y den refugio a la fauna local."
    ),
    "impacto_esperado": (
        "Más de 500 árboles sembrados, con seguimiento mensual durante un año para asegurar que "
        "al menos el 80 % sobreviva. Cada árbol ayuda a frenar la erosión y a regular el agua "
        "que baja hacia los barrios de la zona."
    ),
    "actividades_voluntario": (
        "• Preparar el terreno y abrir los hoyos.\n"
        "• Sembrar las plántulas y colocar tutores y protectores.\n"
        "• Acarrear tierra negra, hojarasca y agua.\n"
        "• Marcar y registrar cada árbol sembrado con su número.\n"
        "• Recoger los residuos que encontremos en el sendero."
    ),
    "perfil_beneficiarios": (
        "Cerca de 1.200 habitantes de los barrios Villa del Cerro y San Luis, que dependen de "
        "la quebrada y sufren deslizamientos en época de lluvias, además de la fauna silvestre "
        "de la reserva."
    ),
    "que_llevar": (
        "Botas de caucho o zapatos cerrados que se puedan ensuciar, ropa cómoda de manga larga, "
        "gorra o sombrero, impermeable liviano, botella de agua, protector solar y guantes de "
        "trabajo si tienes. Nosotros ponemos las herramientas, las plántulas y el refrigerio."
    ),
    "recomendaciones": (
        "Llega 15 minutos antes de las 7:00 a. m. a la entrada de la Quebrada La Vieja. "
        "Desayuna bien y avisa con anticipación si tienes alguna alergia, condición médica o "
        "restricción de movilidad. En caso de lluvia fuerte la jornada se reprograma y te "
        "avisaremos por correo."
    ),
    "politica_cancelacion": (
        "Si no puedes asistir, cancela tu postulación con al menos 48 horas de anticipación para "
        "que otra persona pueda ocupar tu cupo. Si faltas sin avisar dos veces seguidas, podríamos "
        "limitar tus próximas postulaciones."
    ),
    "requisitos_adicionales": (
        "Ser mayor de 16 años (los menores de 18 deben presentar la autorización firmada de su "
        "acudiente) y tener buen estado de salud para caminar unos 20 minutos por terreno "
        "inclinado."
    ),
}


async def main() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        fund = (
            await db.execute(
                select(Fundacion)
                .join(Usuario, Usuario.id == Fundacion.usuario_id)
                .where(Usuario.email == "fundacion1@demo.com")
            )
        ).scalar_one_or_none()
        if fund is None:
            print("No existe la fundación de fundacion1@demo.com.")
            return
        ya = (
            await db.execute(
                select(Publicacion.id).where(
                    Publicacion.fundacion_id == fund.id, Publicacion.titulo == TITULO
                )
            )
        ).first()
        if ya:
            print("La convocatoria ya existe; no se duplica.")
            return

        area = (
            await db.execute(
                select(AreaImpacto).where(AreaImpacto.nombre == "Reforestación y Conservación")
            )
        ).scalar_one_or_none()
        if area is None:
            area = (
                await db.execute(select(AreaImpacto).where(AreaImpacto.nombre == "Medio Ambiente"))
            ).scalar_one()
        muni = (
            await db.execute(select(Municipio).where(Municipio.nombre.ilike("Bogot%")).limit(1))
        ).scalar_one_or_none() or (await db.execute(select(Municipio).limit(1))).scalar_one()

        terminos = ["equipo", "comunic", "organiz", "agric", "jard", "ambient", "liderazgo"]
        habs = list(
            (
                await db.execute(
                    select(Habilidad)
                    .where(or_(*[Habilidad.nombre.ilike(f"%{t}%") for t in terminos]))
                    .limit(5)
                )
            ).scalars().all()
        )
        if len(habs) < 3:
            habs = list((await db.execute(select(Habilidad).limit(4))).scalars().all())

        portada = f"{settings.upload_public_base}/convocatorias/reforestacion-01.jpg"
        pub = Publicacion(
            fundacion_id=fund.id,
            titulo=TITULO,
            descripcion=DESCRIPCION,
            categoria_id=area.id,
            modalidad="PRESENCIAL",
            municipio_id=muni.id,
            direccion_exacta="Entrada Quebrada La Vieja, Calle 71 con Carrera 2 Este, Bogotá",
            fecha_inicio=date(2026, 12, 12),
            fecha_fin=date(2026, 12, 12),
            hora_inicio=time(7, 0),
            hora_fin=time(13, 0),
            cupo_maximo=40,
            edad_minima=16,
            imagen=portada,
            contacto_nombre="Laura Martínez, coordinadora de voluntariado",
            contacto_email="fundacion1@demo.com",
            contacto_telefono="3105550142",
            incluye_transporte=False,
            incluye_alimentacion=True,
            incluye_seguro=True,
            otorga_certificado=True,
            horas_reconocidas=6,
            nivel_experiencia="Ninguno, nosotros te enseñamos",
            fecha_limite_postulacion=date(2026, 12, 9),
            dificultad="MEDIA",
            urgente=False,
            estado="PUBLICADA",
            **DATOS,
        )
        from datetime import UTC, datetime

        pub.fecha_publicacion = datetime.now(UTC)
        db.add(pub)
        await db.flush()
        for h in habs:
            await db.execute(
                insert(publicacion_habilidades).values(publicacion_id=pub.id, habilidad_id=h.id)
            )
        for i in range(1, 6):
            db.add(
                PublicacionImagen(
                    publicacion_id=pub.id,
                    ruta=f"{settings.upload_public_base}/convocatorias/reforestacion-0{i}.jpg",
                    orden=i - 1,
                )
            )
        await db.commit()
        print(f"Convocatoria creada con {len(habs)} habilidades y 5 fotos: {pub.id}")


if __name__ == "__main__":
    # psycopg async en Windows necesita SelectorEventLoop (el Proactor no sirve).
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())
