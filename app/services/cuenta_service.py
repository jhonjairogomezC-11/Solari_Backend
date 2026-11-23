"""Preferencias de notificación y trayectoria/historial del voluntario."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cuenta import PreferenciasNotificacion
from app.models.fundacion import Fundacion
from app.models.gamificacion import VoluntarioPuntos
from app.models.postulacion import (
    ESTADO_ASISTIO,
    Postulacion,
)
from app.models.publicacion import Publicacion
from app.models.voluntario import Voluntario


class CuentaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Preferencias de notificación ──
    async def preferencias(self, usuario_id: uuid.UUID) -> PreferenciasNotificacion:
        pref = await self.db.get(PreferenciasNotificacion, usuario_id)
        if pref is None:
            pref = PreferenciasNotificacion(usuario_id=usuario_id)
            self.db.add(pref)
            await self.db.commit()
            await self.db.refresh(pref)
        return pref

    async def guardar_preferencias(
        self, usuario_id: uuid.UUID, data: dict
    ) -> PreferenciasNotificacion:
        pref = await self.preferencias(usuario_id)
        for key, value in data.items():
            setattr(pref, key, value)
        await self.db.commit()
        await self.db.refresh(pref)
        return pref

    # ── Trayectoria / historial ──
    async def trayectoria(self, voluntario: Voluntario) -> dict:
        # Historial completo de postulaciones con datos de la convocatoria y fundación.
        stmt = (
            select(Postulacion, Publicacion, Fundacion.nombre)
            .join(Publicacion, Publicacion.id == Postulacion.publicacion_id)
            .join(Fundacion, Fundacion.id == Publicacion.fundacion_id)
            .where(Postulacion.voluntario_id == voluntario.id)
            .order_by(Postulacion.fecha_postulacion.desc())
        )
        filas = (await self.db.execute(stmt)).all()

        historial = [
            {
                "postulacion_id": post.id,
                "publicacion_id": pub.id,
                "titulo": pub.titulo,
                "fundacion_nombre": fund_nombre,
                "estado": post.estado,
                "fecha_inicio": pub.fecha_inicio,
                "horas_reconocidas": pub.horas_reconocidas or 0,
                "otorga_certificado": pub.otorga_certificado,
                "calificacion": post.calificacion,
            }
            for (post, pub, fund_nombre) in filas
        ]

        # Fundaciones distintas con las que colaboró (actividades asistidas).
        fundaciones_colaboradas = (
            await self.db.execute(
                select(func.count(func.distinct(Publicacion.fundacion_id)))
                .select_from(Postulacion)
                .join(Publicacion, Publicacion.id == Postulacion.publicacion_id)
                .where(
                    Postulacion.voluntario_id == voluntario.id,
                    Postulacion.estado == ESTADO_ASISTIO,
                )
            )
        ).scalar_one()

        saldo = await self.db.get(VoluntarioPuntos, voluntario.id)

        return {
            "actividades_completadas": voluntario.actividades_completadas or 0,
            "horas_acumuladas": voluntario.horas_acumuladas or 0,
            "xp_total": saldo.total_historico if saldo else 0,
            "fundaciones_colaboradas": fundaciones_colaboradas,
            "postulaciones_totales": len(historial),
            "historial": historial,
        }
