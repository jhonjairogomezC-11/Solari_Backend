"""Acceso a datos de gamificación: puntos, logros, intereses y ranking."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamificacion import (
    Interes,
    Logro,
    TransaccionPuntos,
    VoluntarioInteres,
    VoluntarioLogro,
    VoluntarioPuntos,
)
from app.models.voluntario import Voluntario


class GamificacionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Puntos ──
    async def puntos_de(self, voluntario_id: uuid.UUID) -> VoluntarioPuntos | None:
        return await self.db.get(VoluntarioPuntos, voluntario_id)

    async def puntos_bloqueado(self, voluntario_id: uuid.UUID) -> VoluntarioPuntos | None:
        stmt = (
            select(VoluntarioPuntos)
            .where(VoluntarioPuntos.voluntario_id == voluntario_id)
            .with_for_update()
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def crear_saldo(self, voluntario_id: uuid.UUID) -> VoluntarioPuntos:
        saldo = VoluntarioPuntos(voluntario_id=voluntario_id, saldo=0, total_historico=0)
        self.db.add(saldo)
        await self.db.flush()
        return saldo

    def registrar_transaccion(
        self,
        voluntario_id: uuid.UUID,
        puntos_total: int,
        motivo: str,
        postulacion_id: uuid.UUID | None = None,
        puntos_base: int = 0,
        puntos_bonus: int = 0,
    ) -> TransaccionPuntos:
        tx = TransaccionPuntos(
            voluntario_id=voluntario_id,
            postulacion_id=postulacion_id,
            puntos_base=puntos_base or puntos_total,
            puntos_bonus=puntos_bonus,
            puntos_total=puntos_total,
            motivo=motivo,
        )
        self.db.add(tx)
        return tx

    async def transacciones(
        self, voluntario_id: uuid.UUID, limite: int = 50
    ) -> list[TransaccionPuntos]:
        stmt = (
            select(TransaccionPuntos)
            .where(TransaccionPuntos.voluntario_id == voluntario_id)
            .order_by(TransaccionPuntos.fecha.desc())
            .limit(limite)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    # ── Logros ──
    async def logros_activos(self) -> list[Logro]:
        stmt = select(Logro).where(Logro.activo.is_(True)).order_by(Logro.umbral)
        return list((await self.db.execute(stmt)).scalars().all())

    async def ids_logros_obtenidos(self, voluntario_id: uuid.UUID) -> set[int]:
        stmt = select(VoluntarioLogro.logro_id).where(
            VoluntarioLogro.voluntario_id == voluntario_id
        )
        return {r[0] for r in (await self.db.execute(stmt)).all()}

    async def logros_obtenidos(self, voluntario_id: uuid.UUID) -> list[VoluntarioLogro]:
        stmt = select(VoluntarioLogro).where(
            VoluntarioLogro.voluntario_id == voluntario_id
        )
        return list((await self.db.execute(stmt)).scalars().all())

    def otorgar_logro(self, voluntario_id: uuid.UUID, logro_id: int) -> VoluntarioLogro:
        vl = VoluntarioLogro(voluntario_id=voluntario_id, logro_id=logro_id)
        self.db.add(vl)
        return vl

    # ── Intereses ──
    async def catalogo_intereses(self) -> list[Interes]:
        stmt = select(Interes).order_by(Interes.nombre)
        return list((await self.db.execute(stmt)).scalars().all())

    async def intereses_de(self, voluntario_id: uuid.UUID) -> list[int]:
        stmt = select(VoluntarioInteres.interes_id).where(
            VoluntarioInteres.voluntario_id == voluntario_id
        )
        return [r[0] for r in (await self.db.execute(stmt)).all()]

    async def reemplazar_intereses(
        self, voluntario_id: uuid.UUID, interes_ids: list[int]
    ) -> None:
        from sqlalchemy import delete

        await self.db.execute(
            delete(VoluntarioInteres).where(
                VoluntarioInteres.voluntario_id == voluntario_id
            )
        )
        for iid in interes_ids:
            self.db.add(
                VoluntarioInteres(voluntario_id=voluntario_id, interes_id=iid)
            )
        await self.db.flush()

    async def interes_ids_validos(self, interes_ids: list[int]) -> set[int]:
        if not interes_ids:
            return set()
        stmt = select(Interes.id).where(Interes.id.in_(interes_ids))
        return {r[0] for r in (await self.db.execute(stmt)).all()}

    # ── Ranking ──
    async def ranking_top(self, limite: int = 1000) -> list[tuple[Voluntario, int, int]]:
        """Devuelve (voluntario, total_historico, posicion) ordenado por puntos."""
        stmt = (
            select(
                Voluntario,
                VoluntarioPuntos.total_historico,
                func.row_number()
                .over(order_by=VoluntarioPuntos.total_historico.desc())
                .label("posicion"),
            )
            .join(VoluntarioPuntos, VoluntarioPuntos.voluntario_id == Voluntario.id)
            .where(VoluntarioPuntos.total_historico > 0)
            .order_by(VoluntarioPuntos.total_historico.desc())
            .limit(limite)
        )
        res = await self.db.execute(stmt)
        return [(row[0], row[1], row[2]) for row in res.all()]

    async def posicion_de(self, voluntario_id: uuid.UUID) -> tuple[int, int, int]:
        """Devuelve (posicion, total_historico, total_voluntarios_con_puntos)."""
        saldo = await self.db.get(VoluntarioPuntos, voluntario_id)
        total_hist = saldo.total_historico if saldo else 0

        total_con_puntos = (
            await self.db.execute(
                select(func.count())
                .select_from(VoluntarioPuntos)
                .where(VoluntarioPuntos.total_historico > 0)
            )
        ).scalar_one()

        if total_hist <= 0:
            return 0, 0, total_con_puntos

        mejores = (
            await self.db.execute(
                select(func.count())
                .select_from(VoluntarioPuntos)
                .where(VoluntarioPuntos.total_historico > total_hist)
            )
        ).scalar_one()
        return mejores + 1, total_hist, total_con_puntos
