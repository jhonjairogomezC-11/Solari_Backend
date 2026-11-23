"""Recomendaciones personalizadas de convocatorias para el voluntario.

Puntuación de afinidad (determinista y explicable), máximo 135:
- hasta +30 según la coincidencia de habilidades (porcentaje de habilidades
  requeridas que el voluntario posee).
- +40 si la categoría de la convocatoria se relaciona con un interés del voluntario
  (comparación tolerante a tildes y plurales).
- +25 si la convocatoria es en el municipio del voluntario.
- +15 si es VIRTUAL/HÍBRIDA, o +10 si coincide con su preferencia de modalidad.
- +10 si aún hay cupo disponible.
- +10 si empieza en los próximos 30 días (prioriza lo accionable).

Filtros duros (nunca se recomienda lo incompatible):
- convocatorias no publicadas, ocultas, ya iniciadas o con fecha límite vencida;
- edad fuera del rango exigido;
- actividades de un solo día que caen en un día no compatible con la disponibilidad
  (ENTRE_SEMANA / FINES_DE_SEMANA);
- convocatorias a las que el voluntario ya se postuló.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalogo import AreaImpacto
from app.models.gamificacion import Interes, VoluntarioInteres
from app.models.postulacion import Postulacion
from app.models.publicacion import ESTADO_PUBLICADA, Publicacion
from app.models.voluntario import Voluntario
from app.services.coincidencia import calcular_coincidencia, textos_relacionados
from app.services.habilidad_service import HabilidadService


def _edad(nacimiento: date, hoy: date) -> int:
    return hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))


def es_compatible_con_disponibilidad(pub: Publicacion, disponibilidad: str) -> bool:
    """Una actividad de un solo día solo es compatible si cae en un día disponible."""
    if disponibilidad == "FLEXIBLE" or pub.fecha_inicio != pub.fecha_fin:
        return True
    es_fin_de_semana = pub.fecha_inicio.weekday() >= 5
    if disponibilidad == "ENTRE_SEMANA":
        return not es_fin_de_semana
    if disponibilidad == "FINES_DE_SEMANA":
        return es_fin_de_semana
    return True


class RecomendacionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def recomendar(
        self, voluntario: Voluntario, limite: int = 12
    ) -> list[tuple[Publicacion, int]]:
        hoy = date.today()
        edad = _edad(voluntario.fecha_nacimiento, hoy)

        intereses = (
            await self.db.execute(
                select(Interes.nombre)
                .join(VoluntarioInteres, VoluntarioInteres.interes_id == Interes.id)
                .where(VoluntarioInteres.voluntario_id == voluntario.id)
            )
        ).scalars().all()
        areas = (await self.db.execute(select(AreaImpacto))).scalars().all()
        areas_afines = {
            a.id for a in areas if any(textos_relacionados(a.nombre, i) for i in intereses)
        }
        mis_habilidades = set(await HabilidadService(self.db).ids_de_voluntario(voluntario.id))

        ya_postuladas = set(
            (
                await self.db.execute(
                    select(Postulacion.publicacion_id).where(
                        Postulacion.voluntario_id == voluntario.id
                    )
                )
            )
            .scalars()
            .all()
        )

        stmt = (
            select(Publicacion)
            .options(selectinload(Publicacion.habilidades))
            .where(
                Publicacion.estado == ESTADO_PUBLICADA,
                Publicacion.oculta_por_admin.is_(False),
                Publicacion.fecha_inicio >= hoy,
            )
        )
        candidatas = list((await self.db.execute(stmt)).scalars().all())

        pref_mod = (voluntario.preferencia_modalidad or "").upper()
        resultados: list[tuple[Publicacion, int]] = []
        for pub in candidatas:
            if pub.id in ya_postuladas:
                continue
            if pub.fecha_limite_postulacion and hoy > pub.fecha_limite_postulacion:
                continue
            if pub.edad_minima is not None and edad < pub.edad_minima:
                continue
            if pub.edad_maxima is not None and edad > pub.edad_maxima:
                continue
            if not es_compatible_con_disponibilidad(pub, voluntario.disponibilidad):
                continue

            score = 0
            requeridas = [h.id for h in pub.habilidades]
            score += round(calcular_coincidencia(requeridas, mis_habilidades) * 30 / 100)
            if pub.categoria_id in areas_afines:
                score += 40
            if voluntario.municipio_id and pub.municipio_id == voluntario.municipio_id:
                score += 25
            if pub.modalidad in ("VIRTUAL", "HIBRIDA"):
                score += 15
            elif pref_mod and pub.modalidad == pref_mod:
                score += 10
            if pub.cupo_maximo and pub.cupo_maximo > 0:
                score += 10
            if pub.fecha_inicio <= hoy + timedelta(days=30):
                score += 10
            resultados.append((pub, score))

        resultados.sort(key=lambda x: (x[1], -x[0].fecha_inicio.toordinal()), reverse=True)
        return resultados[:limite]
